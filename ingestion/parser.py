import concurrent.futures
import logging
import os
from pathlib import Path
from dataclasses import dataclass 

from tree_sitter import Parser, Language, Query, QueryCursor

# import config maps

from ingestion.queries import EXTENSION_MAP, LANG_CAPSULES, CHUNK_QUERIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@dataclass
class CodeChunk:
    repo:str
    path:str
    start_line:int
    end_line:int 
    symbol:str 
    kind:str 
    body:str 
    language:str 


class ASTChunker:
    def __init__(self, languages:dict[str, object], queries:dict[str, str], ext_map:dict[str, str]):
        self.ext_map = ext_map
        self.raw_queries = queries
        
        self.parsers: dict[str, Parser] = {}
        self.queries: dict[str, Query] = {}

        for lang_name, capsule in languages.items():
            try:
                ts_lang = Language(capsule)
                self.parsers[lang_name] = Parser(ts_lang)
                if lang_name in queries:
                    self.queries[lang_name] = Query(ts_lang, queries[lang_name])

            except Exception as e:
                logging.error(f"Failed to initialize the tree-sitter for {lang_name}:{e}")


    def chunk_file(self, repo_name: str, file_path: str, content: bytes) -> list[CodeChunk]:
        ext = Path(file_path).suffix.lower()
        lang = self.ext_map.get(ext)

        if not lang or lang not in self.parsers or lang not in self.queries:
            return _fallback_chunk(repo_name, file_path, content, lang or "unknown")

        try:
            parser = self.parsers[lang]
            query = self.queries[lang]
            tree = parser.parse(content)

            cursor = QueryCursor(query)
            matches = cursor.matches(tree.root_node)

            chunks = []
            seen_bytes = set()

            for pattern_index, captures in matches:
                node_list = captures.get("node", [])
                name_list = captures.get("name", [])

                for i, node in enumerate(node_list):
                    sb, eb = node.start_byte, node.end_byte
                    if (sb, eb) in seen_bytes:
                        continue
                    seen_bytes.add((sb, eb))

                    body = content[sb:eb].decode("utf-8", errors="replace")
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1

                    if end_line - start_line < 2:
                        continue

                    symbol = name_list[i].text.decode("utf-8", errors="replace") if i < len(name_list) else f"<anon>:{start_line}"

                    chunks.append(CodeChunk(
                        repo=repo_name, path=file_path,
                        start_line=start_line, end_line=end_line,
                        symbol=symbol, kind="ast_node", body=body, language=lang
                        ))

            return chunks if chunks else self._fallback_chunk(repo_name, file_path, content, lang)
        
        except Exception as e:
            logging.warning(f"Tree-sitter failed on {file_path}, failling back. Error:{e}")
            return self._fallback_chunk(repo_name, file_path, content, lang or "unknown")

    def _fallback_chunk(self, repo_name: str, file_path: str, content: bytes, lang: str, window_size: int = 50, overlap: int = 10) -> list[CodeChunk]:
        """A highly predictable chunker that divides text safely by line increments."""
        lines = content.decode("utf-8", errors="replace").splitlines()
        chunks = []
        
        if not lines:
            return chunks

        idx = 0
        while idx < len(lines):
            end_idx = min(idx + window_size, len(lines))
            body = "\n".join(lines[idx:end_idx])
            
            chunks.append(CodeChunk(
                repo=repo_name, path=file_path,
                start_line=idx + 1, end_line=end_idx,
                symbol=f"{Path(file_path).stem}_block_{idx+1}",
                kind="text_window", body=body, language=lang
            ))
            
            if end_idx == len(lines):
                break
            idx += (window_size - overlap)
            
        return chunks

def _process_single_file(file_info: tuple[Path, Path, str, SimplifiedChunker]) -> list[CodeChunk]:
    """Top-level function wrapper easily picklable by ProcessPoolExecutor."""
    fpath, repo_path, repo_name, chunker = file_info
    try:
        content = fpath.read_bytes()
        if len(content) > 1_000_000: # 1MB limit check
            return []
        rel_path = str(fpath.relative_to(repo_path))
        return chunker.chunk_file(repo_name, rel_path, content)
    except Exception as e:
        logging.error(f"Could not process file {fpath}: {e}")
        return []

def chunk_large_repository(repo_name: str, target_dir: str | Path, chunker: SimplifiedChunker, max_workers: int = None) -> list[CodeChunk]:
    repo_path = Path(target_dir).expanduser().resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path not found: {repo_path}")

    skip_dirs = {".git", "node_modules", "vendor", "target", "__pycache__", "build", "dist"}
    
    file_tasks = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext in chunker.ext_map:
                file_tasks.append((fpath, repo_path, repo_name, chunker))

    logging.info(f"Discovered {len(file_tasks)} target files in {repo_name}. Starting parallel processing...")

    all_chunks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(_process_single_file, file_tasks)
        for chunk_list in results:
            all_chunks.extend(chunk_list)

    logging.info(f"Successfully compiled {len(all_chunks)} chunks from {repo_name}.")
    return all_chunks


