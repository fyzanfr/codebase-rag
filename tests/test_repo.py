import hmac
import hashlib
import json
import requests
from pathlib import Path

SECRET = "real_repo_test_secret"
URL = "http://127.0.0.1:8000/webhook/github"

# Point this to your actual, live local BitGrad repository workspace
REAL_WORKSPACE_DIR = "/home/RYVEN/BitGrad"

# Verify what the latest actual commit hash is in your real workspace
# If you don't know it, you can just use "HEAD" as a valid Git identifier
try:
    from git import Repo
    current_commit = str(Repo(REAL_WORKSPACE_DIR).head.commit)
except Exception:
    current_commit = "HEAD"

# Build the payload mimicking a real GitHub push event
payload = {
    "repository": {
        "name": "BitGrad",
        "clone_url": REAL_WORKSPACE_DIR  # GitPython handles local system paths as clone remotes seamlessly!
    },
    "after": current_commit,
    "commits": [
        {
            "id": current_commit,
            "message": "Testing AST processing pipeline on live repo assets",
            # Supply real paths relative to the root of your BitGrad repository
            "added": ["bitgrad/engine.py", "bitgrad/ops.py"],
            "modified": []
        }
    ]
}

payload_bytes = json.dumps(payload).encode("utf-8")

# Compute signature
mac = hmac.new(SECRET.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
signature = f"sha256={mac.hexdigest()}"

headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": signature
}

print(f"Sending real repository payload targeting commit: {current_commit[:7]}...")
response = requests.post(URL, data=payload_bytes, headers=headers)

print(f"Network Status Code: {response.status_code}")
print(f"Server JSON Response: {response.json()}")
