# git-simplify

git-simplify is a web application that analyzes a software repository and builds an interactive map of how its files, modules, functions, classes, and APIs relate to one another.

Users will be able to connect a Git repository or drag and drop source files for analysis. The project is currently scaffolded; the architecture and interfaces are being established before implementing the analysis pipeline.

## Planned features

- Repository-wide source-file discovery
- Ignore-file and configurable path filtering
- Multi-language parsing through Tree-sitter
- Import and export extraction
- Function, method, class, interface, and variable discovery
- Function and method call extraction
- API and entry-point identification
- Cross-file symbol resolution
- Dependency and call-graph construction
- Circular dependency detection
- Unresolved-reference reporting
- Source locations and metadata for graph entities
- JSON, graph-format, terminal, and interactive exports
- Extensible language and output-format support
- Git repository connection and import workflow
- Drag-and-drop source-file upload
- Interactive browser-based dependency map
- Search, filtering, and relationship inspection
- REST API access for repository analysis

## How it works

git-simplify processes a repository through the following pipeline:

```text
Repository
    ↓
Repository Scanner
    ↓
Source Files
    ↓
Tree-sitter Parser
    ↓
Syntax Trees
    ↓
Import / Symbol / Call Extractors
    ↓
Normalized Entities and Relationships
    ↓
Symbol Resolver
    ↓
Dependency Graph
    ↓
Analysis Services
    ↓
JSON / Graph / Interactive Output
```

## Project architecture

```text
frontend/         Browser application and interactive visualization
backend/          REST API and analysis orchestration
src/git_simplify/  Shared analysis pipeline and graph domain
├── indexer/      Repository scanning and file filtering
├── parser/       Tree-sitter parser and grammar management
├── extractor/    Imports, symbols, calls, and APIs
├── graph/        Graph models and construction
├── analysis/     Relationship analysis and symbol resolution
├── output/       JSON, graph, and interactive exporters
└── config/       Project configuration
```

### Core graph model

The graph will support nodes such as:

- Repository
- Directory
- File
- Module
- Class
- Function
- Method
- API
- External package

Relationships will include:

- `contains`
- `imports`
- `exports`
- `defines`
- `calls`
- `inherits`
- `implements`
- `references`
- `depends_on`

Each node and relationship is expected to retain useful metadata, including source path, line and column range, language, visibility, and resolution status.

## Web application

The frontend will provide two primary ingestion flows:

```text
Connect Git repository → Select branch or commit → Start analysis
Drag and drop files   → Upload source files    → Start analysis
```

The resulting graph will be displayed in the browser with navigation, search, filtering, and relationship details.

## REST API

The backend will expose REST endpoints for:

- Creating an analysis from a connected Git repository
- Uploading source files for analysis
- Checking analysis status
- Retrieving graph data and metadata
- Querying files, symbols, and relationships
- Exporting analysis results

The frontend will consume this API, while the backend will coordinate ingestion, parsing, graph construction, and output serialization.

## Output formats

git-simplify is designed to support several output targets:

- JSON for integrations and downstream tooling
- DOT, Mermaid, or similar graph formats
- Terminal summaries and relationship reports
- Self-contained interactive HTML exports

The analysis model will remain independent from the eventual frontend so that a visual interface can be added without coupling it to parsing or graph construction.

## Repository layout

```text
git-simplify/
├── frontend/        Browser application scaffold
├── backend/         REST API scaffold
├── src/git_simplify/  Core analysis pipeline
├── tests/           Parser, extractor, graph, and integration tests
├── docs/            Architecture and design documentation
├── pyproject.toml
└── README.md
```

## Development phases

1. Core indexing and Tree-sitter parsing
2. Static symbol, import, API, and call extraction
3. Relationship resolution and dependency graph construction
4. REST API and repository/file ingestion
5. Interactive frontend visualization
6. Caching, incremental indexing, and collaboration features

## Current status

The repository contains empty frontend and backend scaffolds, the initial Python analysis package, analysis modules, output modules, test directories, and architecture documentation. Feature implementation is planned for the phases above.
