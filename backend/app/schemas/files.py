from pydantic import BaseModel, Field
from typing import List

class UploadResult(BaseModel):
    file: str
    chunks: int

class SearchRequest(BaseModel):
    query: str
    k: int = Field(default=5, ge=1, le=20)

class SearchHit(BaseModel):
    id: str
    document: str
    metadata: dict
    distance: float

class SearchResponse(BaseModel):
    hits: List[SearchHit]