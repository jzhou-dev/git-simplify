"""Best-effort resolution of static imports and named calls."""

from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
import posixpath
import re

from ..extractor import Symbol
from .models import FileAnalysis, ResolvedReference, ResolutionResult, SymbolLocation


class SymbolResolver:
    """Resolve modules without executing code or searching installed packages.

    Python source roots default to the repository and src. JavaScript imports
    must be relative. Default/wildcard imports, re-exported symbols, dynamic
    dispatch and full language scope semantics are not inferred.
    """

    def __init__(
        self, files: tuple[FileAnalysis, ...], source_roots: tuple[str, ...] = ("", "src")
    ) -> None:
        self.files = {file.path: file for file in files}
        if len(self.files) != len(files):
            raise ValueError("File paths must be unique")
        self.source_roots = source_roots

    def search_symbols(self, name: str) -> tuple[SymbolLocation, ...]:
        """Find exact-name declarations, including nested declarations."""
        return tuple(
            SymbolLocation(path, symbol)
            for path, file in sorted(self.files.items())
            for symbol in file.symbols
            if symbol.name == name
        )

    def _top_level(self, path: str, name: str) -> list[Symbol]:
        symbols = self.files[path].symbols
        return [
            symbol for symbol in symbols
            if symbol.name == name and not any(
                other != symbol
                and (other.start_line, other.start_column)
                <= (symbol.start_line, symbol.start_column)
                and (symbol.end_line, symbol.end_column)
                <= (other.end_line, other.end_column)
                for other in symbols
            )
        ]

    def _modules(self, source: FileAnalysis, module: str) -> list[str]:
        if source.language == "python":
            module = module.split(" as ", 1)[0].strip()
            dots = len(module) - len(module.lstrip("."))
            tail = module[dots:].replace(".", "/")
            if dots:
                base = PurePosixPath(source.path).parent
                for _ in range(dots - 1):
                    if base == PurePosixPath("."):
                        return []
                    base = base.parent
                bases = [str(base / tail)]
            else:
                bases = [str(PurePosixPath(root) / tail) for root in self.source_roots]
            candidates = [p for base in bases for p in (base + ".py", base + "/__init__.py")]
        else:
            if not module.startswith(("./", "../")):
                return []
            base = posixpath.normpath(str(PurePosixPath(source.path).parent / module))
            if base == ".." or base.startswith("../"):
                return []
            candidates = [base]
            if not PurePosixPath(base).suffix:
                candidates += [base + ext for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")]
                candidates += [base + "/index" + ext for ext in (".ts", ".tsx", ".js", ".jsx")]
            elif base.endswith(".js") and base not in self.files:
                candidates += [base[:-3] + ".ts", base[:-3] + ".tsx"]
        return sorted({posixpath.normpath(p) for p in candidates if posixpath.normpath(p) in self.files})

    @staticmethod
    def _names(clause: str) -> list[tuple[str, str]]:
        """Decode simple named import clauses into (original, local) pairs."""
        clause = clause.strip().strip("(){}").strip()
        pairs = []
        for part in clause.split(","):
            match = re.fullmatch(r"\s*(\w+)(?:\s+as\s+(\w+))?\s*", part)
            if match:
                pairs.append((match[1], match[2] or match[1]))
        return pairs

    def resolve(self) -> ResolutionResult:
        imports = []
        calls = []
        for path, file in sorted(self.files.items()):
            bindings: dict[str, list[tuple[str, Symbol | None]]] = defaultdict(list)
            ambiguous_bindings: set[str] = set()
            for ref in file.imports:
                record_index = len(imports)
                targets = self._modules(file, ref.module)
                status = "resolved" if len(targets) == 1 else "ambiguous" if targets else "unresolved"
                imports.append(ResolvedReference(path, ref, status, targets[0] if len(targets) == 1 else None))
                if ref.kind != "import":
                    continue
                if file.language == "python" and ref.name is None:
                    local = ref.module.split(" as ", 1)[-1].strip()
                    if len(targets) > 1:
                        ambiguous_bindings.add(local)
                    for target in targets:
                        bindings[local].append((target, None))
                elif file.language != "python" and ref.name and ref.name.startswith("* as "):
                    if len(targets) > 1:
                        ambiguous_bindings.add(ref.name[5:].strip())
                    for target in targets:
                        bindings[ref.name[5:].strip()].append((target, None))
                elif ref.name and (file.language == "python" or ref.name.strip().startswith("{")):
                    for original, local in self._names(ref.name):
                        if len(targets) > 1:
                            ambiguous_bindings.add(local)
                        for target in targets:
                            bindings[local].extend((target, s) for s in self._top_level(target, original))
                        if file.language == "python" and not bindings[local]:
                            child = ref.module + ("" if ref.module.endswith(".") else ".") + original
                            children = self._modules(file, child)
                            if len(children) > 1:
                                ambiguous_bindings.add(local)
                                imports.append(ResolvedReference(path, ref, "ambiguous"))
                            elif children:
                                bindings[local].append((children[0], None))
                                imports.append(ResolvedReference(path, ref, "resolved", children[0]))
                if imports[record_index].status == "unresolved" and len(imports) > record_index + 1:
                    imports.pop(record_index)
            for ref in file.calls:
                matches: list[tuple[str, Symbol]] = []
                matches.extend((path, symbol) for symbol in self._top_level(path, ref.function))
                matches.extend((target, symbol) for target, symbol in bindings.get(ref.function, []) if symbol is not None)
                for local, destinations in bindings.items():
                    prefix = local + "."
                    if ref.function.startswith(prefix):
                        name = ref.function[len(prefix):]
                        for target, symbol in destinations:
                            if symbol is None:
                                matches.extend((target, s) for s in self._top_level(target, name))
                matches = list(dict.fromkeys(matches))
                status = "resolved" if len(matches) == 1 else "ambiguous" if matches else "unresolved"
                if any(ref.function == name or ref.function.startswith(name + ".") for name in ambiguous_bindings):
                    status = "ambiguous"
                    matches = []
                target, symbol = matches[0] if len(matches) == 1 else (None, None)
                calls.append(ResolvedReference(path, ref, status, target, symbol))
        return ResolutionResult(tuple(imports), tuple(calls))
