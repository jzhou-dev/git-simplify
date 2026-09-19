"""Behavioral tests using real parsers and temporary repositories."""

import json
from pathlib import Path
import tempfile
import unittest

from git_simplify.analysis import (
    FileAnalysis, ProjectAnalyzer, RelationshipAnalyzer, ResolutionResult,
    ResolvedReference, SymbolResolver, analyze_project,
)
from git_simplify.extractor import ImportReference


class ProjectAnalysisTests(unittest.TestCase):
    def analyze(self, sources):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in sources.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            return analyze_project(root)

    def test_python_import_aliases_calls_and_locations(self):
        result = self.analyze({
            'src/pkg/__init__.py': '',
            'src/pkg/util.py': 'def work():\n    pass\n',
            'src/pkg/main.py': 'from .util import work as run\nimport pkg.util as u\nrun()\nu.work()\nprint(1)\n',
        })
        self.assertEqual(result.relationships.dependencies_of('src/pkg/main.py'), ('src/pkg/util.py',))
        calls = result.resolution.calls
        self.assertEqual([c.status for c in calls], ['resolved', 'resolved', 'unresolved'])
        self.assertEqual(calls[0].target_symbol.name, 'work')
        self.assertEqual(calls[0].target_symbol.start_line, 0)
        self.assertEqual(calls[0].reference.start_line, 2)
        self.assertEqual(calls[1].target_path, 'src/pkg/util.py')
        self.assertEqual(SymbolResolver(result.files).search_symbols('work')[0].path, 'src/pkg/util.py')
        self.assertEqual(json.loads(json.dumps(result.to_dict()))['files'][0]['path'], 'src/pkg/__init__.py')

    def test_python_parent_and_submodule_imports(self):
        result = self.analyze({
            'pkg/__init__.py': '',
            'pkg/util.py': 'def work():\n    pass\n',
            'pkg/sub/main.py': 'from .. import util\nutil.work()\n',
        })
        self.assertEqual(result.resolution.calls[0].target_path, 'pkg/util.py')
        self.assertIn('pkg/util.py', result.relationships.dependencies_of('pkg/sub/main.py'))

    def test_javascript_named_namespace_and_reexport(self):
        result = self.analyze({
            'web/lib/index.ts': 'export function work() {}\n',
            'web/main.ts': 'import { work as run } from "./lib";\nimport * as util from "./lib";\nrun(); util.work();\n',
            'web/barrel.ts': 'export { work } from "./lib";\n',
        })
        self.assertEqual([c.status for c in result.resolution.calls], ['resolved', 'resolved'])
        self.assertEqual(result.relationships.dependencies_of('web/barrel.ts'), ('web/lib/index.ts',))

    def test_explicit_js_extension_resolves_typescript(self):
        result = self.analyze({
            'main.ts': 'import { work } from "./util.js"; work();',
            'util.ts': 'export function work() {}',
        })
        self.assertEqual(result.resolution.calls[0].target_path, 'util.ts')

    def test_cycles_and_transitive_dependents(self):
        result = self.analyze({
            'a.py': 'import b\n', 'b.py': 'import c\n',
            'c.py': 'import a\n', 'd.py': 'import a\n', 'alone.py': '',
        })
        relationships = result.relationships
        self.assertEqual(relationships.cycles, (('a.py', 'b.py', 'c.py'),))
        self.assertEqual(relationships.dependents_of('c.py', transitive=True), ('a.py', 'b.py', 'd.py'))
        self.assertEqual(relationships.dependencies_of('d.py', transitive=True), ('a.py', 'b.py', 'c.py'))
        self.assertEqual(relationships.dependencies_of('alone.py'), ())
        with self.assertRaises(KeyError):
            relationships.dependencies_of('missing.py')

    def test_ambiguous_import_and_duplicate_declarations(self):
        result = self.analyze({
            'main.py': 'import util\n', 'util.py': '', 'src/util.py': '',
            'duplicate.py': 'def work(): pass\ndef work(): pass\nwork()\n',
        })
        self.assertEqual(result.resolution.imports[0].status, 'ambiguous')
        self.assertEqual(result.resolution.calls[0].status, 'ambiguous')
        self.assertEqual(result.relationships.dependencies_of('main.py'), ())

    def test_ambiguous_module_does_not_resolve_a_unique_named_symbol(self):
        result = self.analyze({
            'main.py': 'from util import work\nwork()\n',
            'util.py': 'def work(): pass\n',
            'src/util.py': '',
        })
        self.assertEqual(result.resolution.calls[0].status, 'ambiguous')
        self.assertIsNone(result.resolution.calls[0].target_path)

    def test_namespace_package_child_and_custom_source_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'lib/pkg').mkdir(parents=True)
            (root / 'lib/pkg/util.py').write_text('def work(): pass\n')
            (root / 'main.py').write_text('from pkg import util\nutil.work()\n')
            result = ProjectAnalyzer(source_roots=('lib',)).analyze(root)
        self.assertEqual(result.relationships.dependencies_of('main.py'), ('lib/pkg/util.py',))
        self.assertEqual([r.status for r in result.resolution.imports], ['resolved'])
        self.assertEqual(result.resolution.calls[0].target_path, 'lib/pkg/util.py')

    def test_unknown_calls_are_not_matched_to_unrelated_or_nested_symbols(self):
        result = self.analyze({
            'main.py': 'def outer():\n    def hidden(): pass\nhidden()\nwork()\n',
            'util.py': 'def work(): pass\n',
        })
        self.assertTrue(all(c.status == 'unresolved' for c in result.resolution.calls))

    def test_syntax_errors_api_deduplication_and_filtering(self):
        result = self.analyze({
            'broken.py': 'def broken(:\n pass\n',
            'api.py': '@app.get("/health")\ndef health(): pass\n',
            '.hidden.py': 'def hidden(): pass',
            'node_modules/lib/main.js': 'function hidden() {}',
            'notes.txt': 'hello',
            'main.rs': 'fn main() {}',
        })
        self.assertEqual([f.path for f in result.files], ['api.py', 'broken.py'])
        self.assertTrue(result.files[1].has_syntax_errors)
        self.assertEqual(len(result.files[0].apis), 1)

    def test_repeated_analysis_has_no_stale_results(self):
        analyzer = ProjectAnalyzer()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'main.py'
            path.write_text('def old(): pass\n')
            first = analyzer.analyze(directory)
            path.write_text('def new(): pass\n')
            second = analyzer.analyze(directory)
        self.assertEqual(first.files[0].symbols[0].name, 'old')
        self.assertEqual(second.files[0].symbols[0].name, 'new')
        self.assertEqual(self.analyze({}).files, ())

    def test_outside_symlink_is_excluded(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.py'
            target.write_text('def secret(): pass')
            (Path(directory) / 'linked.py').symlink_to(target)
            self.assertEqual(analyze_project(directory).files, ())

    def test_missing_repository_and_non_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                analyze_project(Path(directory) / 'missing')
            path = Path(directory) / 'file'
            path.touch()
            with self.assertRaises(NotADirectoryError):
                analyze_project(path)

    def test_long_dependency_chain_and_self_cycle(self):
        files = tuple(FileAnalysis(f'{i}.py', 'python') for i in range(1200))
        imports = tuple(
            ResolvedReference(f'{i}.py', ImportReference(str(i+1), None, None, 'import', 1, 1, 1, 2), 'resolved', f'{i+1}.py')
            for i in range(1199)
        )
        relationships = RelationshipAnalyzer().analyze(files, ResolutionResult(imports, ()))
        self.assertEqual(relationships.cycles, ())
        self.assertEqual(len(relationships.dependencies_of('0.py', transitive=True)), 1199)
        self.assertEqual(self.analyze({'self.py': 'import self'}).relationships.cycles, (('self.py',),))


if __name__ == '__main__':
    unittest.main()
