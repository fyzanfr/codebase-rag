from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class CodeChunk:
    repo: str
    path: str
    start_line: int
    end_line: int
    symbol: str
    kind: str
    body: str
    language: str
    summary: str = ""
    dense_vector: list[float] | None = None
    sparse_vector: dict[str, list] | None = None
    is_generated: bool = False

    def anchor(self) -> str:
        return f"{self.repo}/{self.path}:{self.start_line}-{self.end_line}"

    def __hash__(self) -> int:
        return hash(self.anchor())

