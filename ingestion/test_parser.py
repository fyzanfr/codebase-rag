import os
from pathlib import Path 

import tree_sitter_python as tspython 
import tree_sitter_typescript as tstypescript 
import tree_sitter_rust as tsrust 
import tree_sitter_go as tsgo 
import tree_sitter_java as tsjava 
from tree_sitter import Language, Parser, Query, QueryCursor
from models.chunk import CodeChunk


_LangCapsules: dict[str, object] = {
        "python": tspython.language(),
        "typscript": tstypescript.language_typescript(),
        "tsx": tstypescript.language_tsx(),
        "rust": tsrust.language(),
        "go": tsgo.language(),
        "java": tsjava.language(),
}

_ext_to_lang: dict[str, str] = {
        ".py":   "python",   ".ts":  "typescript", ".tsx": "tsx",
        ".rs":   "rust",     ".go":  "go",         ".java": "java",
        ".js":   "typescript", ".jsx": "tsx",
        ".c":    "cpp",      ".h":   "cpp",        ".cpp": "cpp",
        ".hpp":  "cpp",      ".rb":  "ruby",       ".zig": "zig",
}

_ts_query = """
    (function_declaration
      name: (identifier) @name
      body: (statement_block) @body) @node
    (method_definition
      name: (property_identifier) @name
      body: (statement_block) @body) @node
    (class_declaration
      name: (type_identifier) @name
      body: (class_body) @body) @node
    (interface_declaration
      name: (type_identifier) @name
      body: (interface_body) @body) @node
    (export_statement
      (function_declaration
        name: (identifier) @name
        body: (statement_block) @body) @node)
    (export_statement
      (class_declaration
        name: (type_identifier) @name
        body: (class_body) @body) @node)
    (export_statement
      (interface_declaration
        name: (type_identifier) @name
        body: (interface_body) @body) @node)
"""

_chunk_queries: dict[str, str] = {
    "python": """
    (function_definition
     name: (identifier) @name
     body: (block) @body) @node
    (class_definition
     name: (identifier) @name
     body: (block) @body) @node
    """,
    "typescript": _ts_query,
    "tsx": _ts_query,
    "rust": """
        (function_item
          name: (identifier) @name
          body: (block) @body) @node
        (struct_item
          name: (type_identifier) @name) @node
        (impl_item
          body: (declaration_list) @body) @node
    """,
    "go": """
        (function_declaration
          name: (identifier) @name
          body: (block) @body) @node
        (method_declaration
          name: (field_identifier) @name
          body: (block) @body) @node
        (type_declaration
          (type_spec name: (type_identifier) @name)) @node
    """,
    "java": """
        (method_declaration
          name: (identifier) @name
          body: (block) @body) @node
        (class_declaration
          name: (identifier) @name
          body: (class_body) @body) @node
        (interface_declaration
          name: (identifier) @name
          body: (interface_body) @body) @node
    """,
}


class ASTChunker:
    def __init__(self) -> None:
        self._parsers: dict[str, Parser | None] = {}
        self._queries: dict[str, Query | None] = {}

    def _get_parser(self, lang:str) -> Parser | None:
        if lang in self._parsers:
            return self._parsers[lang]
        capsule = _LangCapsules.get(lang)
        if capsule is None:
            self._parsers[lang] = None
            return None 
        try:
            py_lang = Language(capsule)
            parser = Parser(py_lang)
            self._parsers[lang] = parser
        except:
            self._parsers[lang] = None 
        return self._parsers[lang]

    def _get_queries(self, lang:str) -> Query | None:
        if lang in self._queries:
            return self._queries[lang]
        qs = _chunk_queries.get(lang)
        capsule = _LangCapsules.get(lang)
        if not qs or capsule is None:
            self._queries[lang] = None 
            return None 
        try:
            qs_lang = Language(capsule)
            query = Query(qs_lang, qs)
            self._queries[lang] = query 
        except:
            self._queries[lang] = None 
            return None
        return self._queries[lang]

    def _get_language(self, file_path:str) -> str | None:
        return _ext_to_lang.get(Path(file_path).suffix.lower())


    def chunk_file(self, repo_name: str, file_path: str, content: bytes) -> list[CodeChunk]:

        lang = self._get_language(file_path)
        if lang is None:
            return self._fallback_chunks(repo_name, file_path, content)

        parser = self._get_parser(lang)
        if parser is None:
            return self._fallback_chunks(repo_name, file_path, content)

        tree = parser.parse(content)
        root = tree.root_node

        query = self._get_queries(lang)
        if query is None:
            return self._fallback_chunks(repo_name, file_path, content)

        cursor = QueryCursor(query)
        matches = cursor.matches(root)

        chunks: list[CodeChunk] = []
        seen_bytes: set[tuple[int, int]] = set()

        for pattern_index, captures in matches:
            node_nodes = captures.get("node", [])
            name_nodes = captures.get("name", [])
            body_nodes = captures.get("body", [])
            trait_nodes = captures.get("trait", [])

            for i, node in enumerate(node_nodes):
                sb, eb = node.start_byte, node.end_byte
                if (sb, eb) in seen_bytes or eb - sb < 4:
                    continue
                seen_bytes.add((sb, eb))

                body = content[sb:eb].decode("utf-8", errors="replace")
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                if end_line - start_line < 2:
                    continue

                symbol = ""
                if i < len(name_nodes):
                    symbol = name_nodes[i].text.decode("utf-8", errors="replace")

                kind = self._classify_kind(lang, pattern_index)
                if not symbol:
                    symbol = f"<anon>:{start_line}"

                chunks.append(CodeChunk(
                    repo_name=repo, path=file_path,
                    start_line=start_line, end_line=end_line,
                    symbol=symbol, kind=kind, body=body, language=lang,
                    ))

        return chunks or self._fallback_chunks(repo, file_path, content)


    def _fallback_chunks(self, repo: str, file_path: str, content: bytes) -> list[CodeChunk]:
        """Naive line-group chunking when tree-sitter is unavailable."""
        lines = content.decode("utf-8", errors="replace").splitlines()
        chunks: list[CodeChunk] = []
        start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "//", "/*")):
                if stripped.endswith(":") and not line[0] in (" ", "\t"):
                    if i - start >= 3:
                        body = "\n".join(lines[start:i])
                        chunks.append(CodeChunk(
                            repo=repo, path=file_path,
                            start_line=start + 1, end_line=i,
                            symbol=stripped.split("(")[0].rstrip(":"),
                            kind="block", body=body, language="unknown",
                        ))
                    start = i
        if len(lines) - start >= 3:
            chunks.append(CodeChunk(
                repo=repo, path=file_path,
                start_line=start + 1, end_line=len(lines),
                symbol=Path(file_path).stem, kind="file",
                body="\n".join(lines[start:]), language="unknown",
            ))
        return chunks 

    def _classify_kind(self, lang: str, pattern_idx: int) -> str:
        mapping = {
             "python":     ["function", "class"],
             "typescript": ["function", "method", "class", "interface", "function", "class", "interface"],
             "tsx":        ["function", "method", "class", "interface", "function", "class", "interface"],
             "rust":       ["function", "struct", "impl"],
             "go":         ["function", "method", "type"],
             "java":       ["method", "class", "interface"],
        }
        kinds = mapping.get(lang, ["function"])
        return kinds[pattern_idx] if pattern_idx < len(kinds) else "function"


def chunk_repository(repo_name:str, repo_path:Path, chunker: ASTChunker | None = None) -> list[CodeChunk]:
    repo_path = Path(repo_path).expanduser().resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"The repository path {repo_path} does not exist.")

    if chunker is None:
        chunker = ASTChunker()
        
    all_chunks: list[CodeChunk] = []
    skip_dirs = {".", "node_modules", "vendor", "target", "__pycache__", "build", "dist", ".git", ".hg"}
    skip_files = {"package-lock.json", "yarn.lock", "Cargo.lock", "go.sum"}

    

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for fname in files:
            if fname in skip_files:
                continue
            ext = Path(fname).suffix.lower()
            if ext not in _ext_to_lang:
                continue
            fpath = Path(root) / fname 
            try:
                content = fpath.read_bytes()
                if len(content) > 500_000:
                    continue 
                rel = str(fpath.relative_to(repo_path.parent))
                all_chunks.extend(chunker.chunk_file(repo_name, rel, content))
            except Exception:
                continue

    return all_chunks


