from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.tenancy import resolve_tenant, get_scope

router = APIRouter()


class GenerateRequest(BaseModel):
    query: str
    client_id: str | None = None
    task_type: str = "chat"
    stream: bool = False


@router.post("/generate")
async def generate_response(
    request: GenerateRequest,
    tenant: tuple = Depends(resolve_tenant)
):
    key_type, app_id, token_client_id = tenant
    
    client_id = token_client_id or request.client_id
    scope = get_scope(app_id, client_id)
    
    # TODO: Retrieve + LLM call
    
    return {
        "answer": f"Demo response for '{request.query}' from scope {scope}",
        "model_used": "groq/llama-3.3-70b",
        "tokens_in": 150,
        "tokens_out": 80,
        "cost_usd": 0.002,
        "sources": []
    }