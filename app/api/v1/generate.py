from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.core.tenancy import resolve_tenant, get_scope
from app.services.llm_router import LLMRouter

router = APIRouter()


class GenerateRequest(BaseModel):
    query: str
    client_id: str | None = None
    task_type: str = "chat"
    stream: bool = False
    max_tokens: int = 1024
    temperature: float = 0.7


@router.post("/generate")
async def generate_response(
    request: GenerateRequest,
    tenant: tuple = Depends(resolve_tenant)
):
    key_type, app_id, token_client_id = tenant
    
    client_id = token_client_id or request.client_id
    scope = get_scope(app_id, client_id)
    
    # Prepare messages
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": request.query}
    ]
    
    if request.stream:
        # Streaming response
        async def stream_response():
            stream = await LLMRouter.generate(
                app_id=app_id,
                client_id=client_id,
                messages=messages,
                task_type=request.task_type,
                stream=True,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            async for chunk in stream:
                yield chunk
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        # Non-streaming response
        result = await LLMRouter.generate(
            app_id=app_id,
            client_id=client_id,
            messages=messages,
            task_type=request.task_type,
            stream=False,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return {
            "answer": result["response"],
            "model_used": result["model_used"],
            "tokens_in": result["input_tokens"],
            "tokens_out": result["output_tokens"],
            "cost_usd": result["cost_usd"],
            "provider": result["provider"],
            "scope": scope,
            "sources": []  # TODO: Add actual retrieval
        }
