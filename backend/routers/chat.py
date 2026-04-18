from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.retrieval import retrieve_answer

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str
    
class GeographicFilters(BaseModel):
    level: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    commune: Optional[str] = None

class ChatRequest(BaseModel):
    question: str
    use_internet: bool = False
    chat_history: List[ChatMessage] = []
    filters: Optional[GeographicFilters] = None
    
class SourceDoc(BaseModel):
    page_content: str
    metadata: dict

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDoc]

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    RAG Endpoint for asking questions about Italian urban planning laws.
    """
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]
    active_filters = request.filters.model_dump(exclude_none=True) if request.filters else {}
    
    answer, source_docs = retrieve_answer(
        question=request.question, 
        use_internet=request.use_internet,
        filters=active_filters,
        chat_history=history_dicts
    )
    return ChatResponse(answer=answer, sources=source_docs)
