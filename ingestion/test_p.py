import os
from pathlib import Path 
from test_parser import MiniASTChunker
# Say you are indexing your own custom framework folder located at: /home/RYVEN/workspace/bitgrad
repo_name = "BitGrad"
repo_path = Path("/home/RYVEN/BitGrad/")

chunker = MiniASTChunker()
all_chunks = []

for root, dirs, files in os.walk(repo_path):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in files:
        fpath = Path(root) / fname  # e.g., PosixPath('/home/RYVEN/workspace/bitgrad/autograd/engine.py')
        
        rel_path = str(fpath.relative_to(repo_path)) # Yields: "autograd/engine.py"
        
        try:
            content_bytes = fpath.read_bytes()

            chunks = chunker.chunk_source(
                    repo_name=repo_name,      
                    file_path=rel_path,     
                    raw_bytes=content_bytes
                )

            all_chunks.append(chunks)

        except Exception as e:
            print(f"Skipping {rel_path} due to error: {e}")
            continue


print(f"Successfully extracted a total of {len(all_chunks)} chunks from the entire repository!")
print(all_chunks[2])
