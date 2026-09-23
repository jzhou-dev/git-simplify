"""Graph storage invariants and end-to-end construction tests."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from git_simplify.analysis import analyze_project
from git_simplify.graph import (
    DependencyGraph, GraphBuilder, GraphEdge, GraphNode, SourceLocation,
    build_graph, graph_id,
)


class DependencyGraphTests(unittest.TestCase):
    def graph(self, names=('a', 'b', 'c', 'd')):
        graph = DependencyGraph()
        for name in names:
            graph.add_node(GraphNode(name, 'file', name))
        return graph

    def test_duplicate_records_and_conflicting_ids(self):
        graph = self.graph()
        graph.add_node(GraphNode('a', 'file', 'a'))
        edge = GraphEdge('ab', 'a', 'b', 'depends_on')
        graph.add_edge(edge)
        graph.add_edge(edge)
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(len(graph.edges), 1)
        with self.assertRaises(ValueError):
            graph.add_node(GraphNode('a', 'file', 'different'))
        with self.assertRaises(ValueError):
            graph.add_edge(replace(edge, target='c'))
        self.assertEqual(graph.get_edge('ab'), edge)
        self.assertEqual(graph.dependencies_of('a'), ('b',))

    def test_dangling_edges_and_unknown_queries(self):
        graph = self.graph()
        with self.assertRaises(ValueError):
            graph.add_edge(GraphEdge('missing', 'a', 'missing', 'calls'))
        self.assertEqual(graph.edges, ())
        for query in (graph.get_node, graph.get_edge, graph.incoming, graph.outgoing,
                      graph.dependencies_of, graph.dependents_of):
            with self.assertRaises(KeyError):
                query('missing')

    def test_direct_transitive_and_filtered_queries(self):
        graph = self.graph()
        for source, target in [('a', 'b'), ('b', 'c'), ('c', 'a'), ('d', 'a')]:
            graph.add_edge(GraphEdge(source + target, source, target, 'depends_on'))
        graph.add_edge(GraphEdge('call', 'a', 'd', 'calls'))
        graph.add_edge(GraphEdge('unresolved', 'b', 'd', 'depends_on', status='unresolved'))
        self.assertEqual(graph.dependencies_of('a'), ('b',))
        self.assertEqual(graph.dependencies_of('a', transitive=True), ('b', 'c'))
        self.assertEqual(graph.dependents_of('c', transitive=True), ('a', 'b', 'd'))
        self.assertEqual(graph.dependencies_of('a', kind='calls'), ('d',))
        self.assertEqual(len(graph.outgoing('a')), 2)
        self.assertEqual(graph.incoming('d', kind='calls')[0].id, 'call')
        self.assertEqual(graph.find_cycles(), (('a', 'b', 'c'),))
        self.assertEqual(graph.find_cycles(kind='calls'), ())

    def test_isolated_nodes_self_loops_and_parallel_edges(self):
        graph = self.graph()
        graph.add_edge(GraphEdge('one', 'a', 'a', 'depends_on'))
        graph.add_edge(GraphEdge('two', 'a', 'a', 'depends_on'))
        self.assertEqual(graph.dependencies_of('a'), ('a',))
        self.assertEqual(graph.dependencies_of('a', transitive=True), ())
        self.assertEqual(graph.find_cycles(), (('a',),))
        self.assertEqual(graph.dependencies_of('b'), ())
        self.assertEqual(DependencyGraph().to_dict(), {'nodes': [], 'edges': []})

    def test_metadata_cannot_mutate_graph(self):
        graph = self.graph()
        metadata = {'nested': ['value']}
        graph.add_node(GraphNode('extra', 'file', 'extra', metadata=metadata))
        graph.add_edge(GraphEdge('edge', 'a', 'extra', 'calls', metadata=metadata))
        metadata['nested'].append('outside')
        graph.get_node('extra').metadata['nested'].append('getter')
        graph.get_edge('edge').metadata['nested'].append('getter')
        exported = graph.to_dict()
        exported['nodes'].clear()
        self.assertEqual(graph.get_node('extra').metadata, {'nested': ['value']})
        self.assertEqual(graph.get_edge('edge').metadata, {'nested': ['value']})
        self.assertEqual(len(graph.nodes), 5)

    def test_invalid_records_are_rejected_without_mutation(self):
        graph = self.graph()
        with self.assertRaises(ValueError):
            graph.add_node(GraphNode('', 'file', 'empty'))
        with self.assertRaises(TypeError):
            graph.add_node(GraphNode('bad', 'file', 'bad', metadata={'bad': object()}))
        with self.assertRaises(ValueError):
            graph.add_edge(GraphEdge('bad', 'a', 'b', 'calls', metadata={'bad': float('nan')}))
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(graph.edges, ())
        for coordinates in [(-1, 0, 0, 1), (2, 0, 1, 0), (1, 5, 1, 4)]:
            with self.assertRaises(ValueError):
                SourceLocation(*coordinates)

    def test_large_cycle_avoids_recursion_limit(self):
        graph = self.graph(tuple(str(i) for i in range(1100)))
        for i in range(1100):
            graph.add_edge(GraphEdge(str(i), str(i), str((i + 1) % 1100), 'depends_on'))
        self.assertEqual(len(graph.find_cycles()[0]), 1100)
        self.assertEqual(len(graph.dependencies_of('0', transitive=True)), 1099)

    def test_ids_encode_boundaries_and_unicode(self):
        self.assertNotEqual(graph_id('file', 'a:b', 'c'), graph_id('file', 'a', 'b:c'))
        self.assertNotEqual(graph_id('file', 'x'), graph_id('symbol', 'x'))
        self.assertEqual(graph_id('file', '日本.py'), graph_id('file', '日本.py'))


class GraphBuilderTests(unittest.TestCase):
    def analyze(self, sources):
        with tempfile.TemporaryDirectory() as directory:
            for name, source in sources.items():
                path = Path(directory) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            return analyze_project(directory)

    def test_builds_hierarchy_symbols_routes_imports_and_calls(self):
        analysis = self.analyze({
            'src/pkg/util.py': 'def work(): pass\n',
            'src/pkg/main.py': 'from .util import work\n@app.get("/health")\ndef health():\n    work()\n',
        })
        graph = build_graph(analysis)
        main = graph_id('file', 'src/pkg/main.py')
        util = graph_id('file', 'src/pkg/util.py')
        self.assertEqual(graph.dependencies_of(main), (util,))
        directories = {node.path for node in graph.nodes if node.kind == 'directory'}
        self.assertEqual(directories, {'src', 'src/pkg'})
        parent = graph.incoming(main, kind='contains')[0].source
        self.assertEqual(graph.get_node(parent).path, 'src/pkg')
        declarations = [graph.get_node(edge.target) for edge in graph.outgoing(main, kind='defines')]
        self.assertEqual({node.name for node in declarations}, {'health', 'GET /health'})
        calls = [edge for edge in graph.outgoing(main, kind='calls') if edge.status == 'resolved']
        self.assertEqual(len(calls), 1)
        target = graph.get_node(calls[0].target)
        self.assertEqual((target.name, target.path), ('work', 'src/pkg/util.py'))
        self.assertEqual(calls[0].location.start_line, 3)
        self.assertEqual(target.location.start_line, 0)
        self.assertEqual(graph.get_node(main).language, 'python')
        json.dumps(graph.to_dict(), allow_nan=False)
        for edge in graph.edges:
            graph.get_node(edge.source)
            graph.get_node(edge.target)

    def test_keeps_occurrences_but_deduplicates_dependencies(self):
        graph = build_graph(self.analyze({
            'a.py': 'import b\nimport b\nb.work()\nb.work()\n',
            'b.py': 'def work(): pass',
        }))
        source = graph_id('file', 'a.py')
        self.assertEqual(len(graph.outgoing(source, kind='imports')), 2)
        self.assertEqual(len(graph.outgoing(source, kind='calls')), 2)
        self.assertEqual(len(graph.outgoing(source, kind='depends_on')), 1)

    def test_unresolved_ambiguous_and_reexport_edges(self):
        graph = build_graph(self.analyze({
            'main.ts': 'import { work } from "./util";\nimport "external";\nunknown();',
            'util.ts': 'export function work() {}',
            'util.js': 'export function work() {}',
            'barrel.ts': 'export { work } from "./util.ts";',
        }))
        source = graph_id('file', 'main.ts')
        imports = graph.outgoing(source, kind='imports')
        self.assertEqual({edge.status for edge in imports}, {'ambiguous', 'unresolved'})
        self.assertEqual(graph.dependencies_of(source), ())
        self.assertTrue(all(graph.get_node(edge.target).kind == 'reference' for edge in imports))
        barrel = graph_id('file', 'barrel.ts')
        self.assertEqual(len(graph.outgoing(barrel, kind='exports')), 1)
        self.assertEqual(graph.dependencies_of(barrel), (graph_id('file', 'util.ts'),))
        self.assertFalse(any(node.kind == 'external_package' for node in graph.nodes))

    def test_cycles_match_analysis(self):
        analysis = self.analyze({'a.py': 'import b', 'b.py': 'import a', 'c.py': ''})
        graph = build_graph(analysis)
        cycles = tuple(tuple(sorted(graph.get_node(node).path for node in cycle)) for cycle in graph.find_cycles())
        self.assertEqual(cycles, analysis.relationships.cycles)

    def test_determinism_reuse_and_checkout_independent_ids(self):
        analysis = self.analyze({'a.py': 'import b\nb.work()', 'b.py': 'def work(): pass'})
        builder = GraphBuilder()
        first = builder.build(analysis)
        reordered = replace(analysis, files=tuple(reversed(analysis.files)), resolution=replace(
            analysis.resolution, imports=tuple(reversed(analysis.resolution.imports))))
        self.assertEqual(first.to_dict(), builder.build(reordered).to_dict())
        relocated = builder.build(replace(analysis, root='/different/checkout'))
        self.assertEqual([node.id for node in first.nodes], [node.id for node in relocated.nodes])
        self.assertEqual(first.edges, relocated.edges)
        empty = builder.build(self.analyze({}))
        self.assertEqual(len(empty.nodes), 1)
        self.assertEqual(empty.edges, ())
        self.assertGreater(len(first.nodes), 1)

    def test_invalid_snapshots_fail_instead_of_creating_dangling_edges(self):
        analysis = self.analyze({'a.py': 'import b', 'b.py': ''})
        reference = analysis.resolution.imports[0]
        for target in (None, 'missing.py'):
            broken = replace(analysis, resolution=replace(analysis.resolution, imports=(replace(reference, target_path=target),)))
            with self.assertRaises(ValueError):
                build_graph(broken)
        with self.assertRaises(ValueError):
            build_graph(replace(analysis, files=(analysis.files[0], analysis.files[0])))
        with self.assertRaises(ValueError):
            build_graph(replace(analysis, files=(replace(analysis.files[0], path='../outside.py'),)))


if __name__ == '__main__':
    unittest.main()
