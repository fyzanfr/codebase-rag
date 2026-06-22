import tree_sitter_python as tspython 
import tree_sitter_typescript as tstypescript 
import tree_sitter_rust as tsrust 
import tree_sitter_go as tsgo 
import tree_sitter_java as tsjava 

# --- Raw Query Strings

_ts_query = """
    (function_declaration name: (identifier) @name body: (statement_block) @body) @node
    (method_definition name: (property_identifier) @name body: (statement_block) @body) @node
    (class_declaration name: (type_identifier) @name body: (class_body) @body) @node
    (interface_declaration name: (type_identifier) @name body: (interface_body) @body) @node
    (export_statement (function_declaration name: (identifier) @name body: (statement_block) @body) @node)
    (export_statement (class_declaration name: (type_identifier) @name body: (class_body) @body) @node)
    (export_statement (interface_declaration name: (type_identifier) @name body: (interface_body) @body) @node)
"""

_python_query = """
    (function_definition name: (identifier) @name body: (block) @body) @node
    (class_definition name: (identifier) @name body: (block) @body) @node
"""

_rust_query = """
    (function_item name: (identifier) @name body: (block) @body) @node
    (struct_item name: (type_identifier) @name) @node
    (impl_item body: (declaration_list) @body) @node
"""

_go_query = """
    (function_declaration name: (identifier) @name body: (block) @body) @node
    (method_declaration name: (field_identifier) @name body: (block) @body) @node
    (type_declaration (type_spec name: (type_identifier) @name)) @node
"""

_java_query = """
    (method_declaration name: (identifier) @name body: (block) @body) @node
    (class_declaration name: (identifier) @name body: (class_body) @body) @node
    (interface_declaration name: (identifier) @name body: (interface_body) @body) @node
"""

# Configuration Maps

EXTENSION_MAP = {
    ".py": "python",
    ".ts": "typescript", ".tsx": "tsx",
    ".js": "typescript", ".jsx": "tsx",
    ".rs": "rust",     ".go": "go", ".java": "java",
}

LANG_CAPSULES = {
    "python": tspython.language(),
    "typescript": tstypescript.language_typescript(),
    "tsx": tstypescript.language_tsx(),
    "rust": tsrust.language(),
    "go": tsgo.language(),
    "java": tsjava.language(),
}

CHUNK_QUERIES = {
    "python": _python_query,
    "typescript": _ts_query, 
    "tsx": _ts_query,
    "rust": _rust_query,
    "go": _go_query,
    "java": _java_query,
}
