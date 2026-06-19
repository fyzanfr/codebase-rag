import logging
from pathlib import Path
from git import Repo
from config import settings
from index.dense import DenseIndex


dense_indexer = DenseIndex()

def async_git_and_parse_worker(repo_name: str, clone_url: str, target_commit: str, changed_files: list[str], chunker):

    local_repo_path = settings.STORAGE_ROOT / repo_name

    try:
        # Disk Alignment
        if not local_repo_path.exists():
            logging.info(f"[{repo_name}] Local mirror missing. Cloning...")
            git_repo = Repo.clone_from(clone_url, local_repo_path)
        else:
            git_repo = Repo(local_repo_path)
            logging.info(f"[{repo_name}] Local mirror exists. Fetching remote changes...")
            git_repo.remotes.origin.fetch()

        logging.info(f"[{repo_name}] Switching working directory to target commit {target_commit[:7]}")
        git_repo.git.checkout(target_commit, force=True)

        all_new_chunks = []
        for rel_path_str in changed_files:
            fpath = local_repo_path / rel_path_str
            if fpath.suffix.lower() in chunker.ext_map and fpath.exists():
                try:
                    if fpath.stat().st_size > settings.MAX_FILE_SIZE_BYTES:
                        continue
                    content = fpath.read_bytes()
                    file_chunks = chunker.chunk_file(repo_name, rel_path_str, content)
                    all_new_chunks.extend(file_chunks)
                except Exception as e:
                    logging.error(f"Failed extraction on file {rel_path_str}: {e}")

        logging.info(f"[{repo_name}] Successfully generated {len(all_new_chunks)} code chunks.")
        if all_new_chunks:
            dense_indexer.index_chunks(all_new_chunks)

    except Exception as e:
        logging.error(f"Background worker failed for repository {repo_name}: {e}")

