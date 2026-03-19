from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()


class ProviderResponse(BaseModel):
    id: str
    name: str
    display_name: str
    status: str
    models: List[dict]


@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers():
    return [
        ProviderResponse(
            id="anthropic",
            name="anthropic",
            display_name="Anthropic Claude",
            status="healthy",
            models=[{"id": "claude-sonnet-4", "name": "Claude Sonnet 4"}]
        ),
        ProviderResponse(
            id="groq",
            name="groq",
            display_name="Groq",
            status="healthy",
            models=[{"id": "llama-3.3-70b", "name": "Llama 3.3 70B"}]
        ),
    ]


@router.post("/providers")
async def add_provider():
    return {"status": "created"}