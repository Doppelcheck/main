from typing import Optional, Dict, Any

# Models for request and response data
from pydantic import BaseModel, HttpUrl


class WebContent(BaseModel):
    html: str
    url: HttpUrl
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None


class RelevantChunk(BaseModel):
    id: str
    content: str
    summary: Optional[str] = None
    importance: float
    entities: Dict[str, float]


class QueryRequest(BaseModel):
    chunk_id: str
    chunk_content: str
    context: Dict[str, Any]


class SearchResult(BaseModel):
    url: HttpUrl
    title: str
    snippet: str


class CompareRequest(BaseModel):
    original_chunk: RelevantChunk
    search_result_url: HttpUrl
    context: Dict[str, Any]
    query: str


class AlignmentResult(BaseModel):
    score: float
    matching_content: Optional[str] = None
    explanation: Optional[str] = None