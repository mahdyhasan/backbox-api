"""
Document query endpoint for RAG
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.tenancy import resolve_tenant, get_scope
from app.services.retrieval_service import retrieval_service
from app.services.embedding_service import embedding_service

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    client_id: str | None = None
    top_k: int = 8


@router.post("/query")
async def query_documents(
    request: QueryRequest,
    tenant: tuple = Depends(resolve_tenant)
):
    """
    Query documents using RAG (Retrieval Augmented Generation)
    
    Flow:
    1. Resolve tenant and scope
    2. Generate query embedding
    3. Search Qdrant for similar chunks
    4. Return ranked results
    """
    key_type, app_id, token_client_id = tenant
    
    # Validation
    if key_type == "app" and not request.client_id and not token_client_id:
        raise HTTPException(400, "client_id required")
    
    client_id = token_client_id or request.client_id
    scope = get_scope(app_id, client_id)
    
    # Step 1: Generate query embedding
    import time
    start_time = time.time()
    
    query_vector = embedding_service._simple_hash_embedding(request.query)
    
    # Step 2: Search Qdrant
    chunks = await retrieval_service.search(
        query_vector=query_vector,
        scope=scope,
        top_k=request.top_k,
        score_threshold=0.3  # Lower threshold for demo embeddings
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Step 3: Format results
    results = []
    for chunk in chunks:
        results.append({
            "text": chunk["text"],
            "score": chunk["score"],
            "source": chunk["metadata"].get("filename", "unknown"),
            "chunk_index": chunk["metadata"].get("chunk_index", 0)
        })
    
    return {
        "query": request.query,
        "scope": scope,
        "chunks": results,
        "latency_ms": latency_ms,
        "total_chunks": len(results)
    }