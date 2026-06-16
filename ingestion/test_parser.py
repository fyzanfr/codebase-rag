import os
from pathlib import Path 

import tree_sitter_python as tspython 
import tree_sitter_typescript as tstypescript 
import tree_sitter_rust as tsrust 
import tree_sitter_go as tsgo 
import tree_sitter_java as tsjava 
from tree_sitter import Language, Parser, Query, QueryCursor 


_LangCapsules: dict[str, object] = {
        "python": tspython.language(),
        "typscript": tstypescript.language(),
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
        if qs or capsule is None:
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


        root_node = self.parser.parse(raw_bytes).root_node
        cursor = QueryCursor(self.query)
        matches = cursor.matches(root_node)

        chunks = []

        for pattern_index, captures in matches:
            node_list = captures.get("node", [])
            name_list = captures.get("name", [])
            
            if not node_list:
                continue
                
            node = node_list[0]
            
            # Extract line coordinates (1-indexed for human readability)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Extract the raw code code body string
            body = raw_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            
            # Extract the literal symbol name string
            symbol = "anonymous"
            if name_list:
                symbol = raw_bytes[name_list[0].start_byte:name_list[0].end_byte].decode("utf-8", errors="replace")
                
            # Classify using our pattern index array lookup
            kind = self.kinds[pattern_index] if pattern_index < len(self.kinds) else "function"
            
            # 5. Pack everything neatly into a structured dictionary
            chunks.append({
                "repo": repo_name,
                "path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "symbol": symbol,
                "kind": kind,
                "body": body,
                "language": "python"
            })
            
        return chunks
