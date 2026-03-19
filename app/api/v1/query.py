from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.tenancy import resolve_tenant, get_scope

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
    key_type, app_id, token_client_id = tenant
    
    if key_type == "app" and not request.client_id and not token_client_id:
        raise HTTPException(400, "client_id required")
    
    client_id = token_client_id or request.client_id
    scope = get_scope(app_id, client_id)
    
    # TODO: Actual Qdrant retrieval
    
    return {
        "query": request.query,
        "scope": scope,
        "chunks": [
            {
                "text": "Demo chunk 1 from " + scope,
                "score": 0.95,
                "source": "demo-doc.pdf"
            }
        ],
        "latency_ms": 45
    }