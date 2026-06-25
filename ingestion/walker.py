import logging
from pathlib import Path
from git import Repo
from config.settings import settings
from index.dense import DenseIndex
from qdrant_client import QdrantClient, models


def delete_vectors_by_path(repo_name: str, file_paths: list[str], qdrant_client: QdrantClient):
    if not file_paths:
        return

    logging.info(f"[{repo_name}] Purging old chunks from Qdrant for {len(file_paths)} files...")
    
    try:
        qdrant_client.delete(
            collection_name=settings.COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(key="repo_name", match=models.MatchValue(value=repo_name)),
                        models.FieldCondition(key="path", match=models.MatchAny(any=file_paths))
                    ]
                )
            )
        )
        logging.info(f"[{repo_name}] Successfully purged old vector history.")
    except Exception as e:
        logging.error(f"[{repo_name}] Metadata vector drop crashed: {e}")


def async_git_and_parse_worker(
        repo_name: str, 
        clone_url: str, 
        target_commit: str, 
        update_paths: list[str],
        delete_paths: list[str],
        chunker
    ):

    dense_indexer = DenseIndex()
    qdrant_client = QdrantClient(
        url=settings.QDRANT_HOST,
        api_key=settings.QDRANT_API_KEY
    )
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

        paths_to_wipe = list(set(update_paths + delete_paths))
        if paths_to_wipe:
            delete_vectors_by_path(repo_name, paths_to_wipe, qdrant_client)


        all_new_chunks = []
        for rel_path_str in update_paths:
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
            logging.info(f"[{repo_name}] Upserting {len(all_new_chunks)} fresh code chunks to Qdrant...")
            dense_indexer.index_chunks(all_new_chunks)
            logging.info(f"[{repo_name}] Upsert processing completely finalized.")
        else:
            logging.info(f"[{repo_name}] No new code chunks required indexing.")


    except Exception as e:
        logging.error(f"Background worker failed for repository {repo_name}: {e}")

