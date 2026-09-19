# git-simplify Architecture

This document will describe the repository indexing, parsing, extraction,
relationship resolution, graph construction, analysis, and output layers.


## Analysis API

`git_simplify.analysis.ProjectAnalyzer` consumes the scanner's
`iter_parsed_files()` iterator, extracts declarations/imports/calls/API routes,
then runs `SymbolResolver` and `RelationshipAnalyzer`. The scanner's original
`scan()` method still parses files and returns `None`.

```python
import json
from git_simplify.analysis import ProjectAnalyzer, SymbolResolver

result = ProjectAnalyzer().analyze("/path/to/repository")
print(result.relationships.cycles)
print(SymbolResolver(result.files).search_symbols("main"))
print(json.dumps(result.to_dict(), indent=2))
```

`ProjectAnalysis` contains:

- `root`: absolute repository path.
- `files`: sorted `FileAnalysis` records with symbols, imports, calls, API routes
  and a syntax-error flag. Paths are repository-relative, with POSIX separators.
- `resolution.imports` and `resolution.calls`: source references, resolution
  statuses (`resolved`, `unresolved`, `ambiguous`) and optional target locations.
- `relationships`: direct dependency/dependent adjacency maps and cycle groups.
  `dependencies_of(path, transitive=True)` and
  `dependents_of(path, transitive=True)` traverse those maps. Unknown paths raise
  `KeyError`; transitive queries exclude the starting file.

Locations retain the extractors' **zero-based** lines and columns. Results retain
no syntax trees and can be serialized with `json.dumps(result.to_dict())`.
Analysis is a fresh snapshot on every invocation; no project code is executed.

## Resolution boundaries

Python module lookup uses the repository root and `src/` by default. Customize
this with `ProjectAnalyzer(source_roots=("", "src", "lib"))`. Relative imports,
package initializers, simple named aliases and module aliases are supported.
JavaScript/TypeScript lookup supports relative files, directory index files,
named aliases, namespace imports, and `.js` references to TypeScript source.
Multiple candidate files or declarations are reported as ambiguous.

Call resolution is a best-effort match against top-level declarations and
imported names, not a language type checker. It does not model local shadowing,
assignment flow, instance methods, default/wildcard imports, re-export chains,
JavaScript export visibility or package/tsconfig resolution. The current import
extractor also does not enumerate every form (for example, all modules in one
Python `import a, b` statement). Such analysis is incomplete and should not be
used as a guarantee that a change is safe. Unresolved references include
builtins, external packages, missing modules and unsupported forms; they are
not automatically errors.

File dependency edges come from imports and re-exports, not calls. Python
`from package import child` can produce both package and child-module edges.
Cycles are strongly connected groups, including self-imports, rather than an
enumeration of every possible cycle path. The traversal is iterative, so long
dependency chains do not consume the Python recursion stack.

Syntax errors are flagged while partial extraction continues. Unsupported
languages are skipped using the existing scanner behavior. File read errors
propagate. File symlinks outside the repository are skipped. Graph rendering,
REST/MCP endpoints, incremental caching, and runtime symbol inference remain
separate work.
