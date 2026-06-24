import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks, status
from config.settings import settings
from ingestion.queries import EXTENSION_MAP, LANG_CAPSULES, CHUNK_QUERIES
from ingestion.parser import ASTChunker
from ingestion.walker import async_git_and_parse_worker

router = APIRouter()

chunker = ASTChunker(LANG_CAPSULES, CHUNK_QUERIES, EXTENSION_MAP)


def verify_signature(payload_bytes: bytes, signature_header: str | None):
    if not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature missing.")
    try:
        hash_type, signature = signature_header.split("=")
        if hash_type != "sha256":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported signature type.")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed signature.")

    mac = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted payload signature.")


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_push_receiver(request: Request, background_tasks: BackgroundTasks, x_hub_signature_256: str | None = Header(None)):
    raw_body = await request.body()
    verify_signature(raw_body, x_hub_signature_256)

    payload = await request.json()
    if "zen" in payload:
        return {"status": "authorized", "message": payload["zen"]}

    repo_data = payload.get("repository", {})
    repo_name = repo_data.get("name")
    clone_url = repo_data.get("clone_url")
    target_commit = payload.get("after")

    if not repo_name or not clone_url or target_commit == "0000000000000000000000000000000000000000":
        return {"status": "ignored"}
    
    files_to_update = set()
    files_to_delete = set()
    
    for commit in payload.get("commits", []):
        files_to_update.update(commit.get("added", []))
        files_to_update.update(commit.get("modified", []))

        files_to_delete.update(commit.get("removed", []))

    files_to_update.difference_update(files_to_delete)

    background_tasks.add_task(
        async_git_and_parse_worker,
        repo_name=repo_name, 
        clone_url=clone_url,
        target_commit=target_commit, 
        update_paths=list(files_to_update),
        delete_paths=list(files_to_delete),
        chunker=chunker 
    )

    return {
            "status": "queued", 
            "repository": repo_name, 
            "commit": target_commit[:7],
            "updating": len(files_to_update),
            "deleting": len(files_to_delete)
        }




