from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class ClientCreate(BaseModel):
    id: str
    name: str
    email: str
    plan: str = "free"


class ClientResponse(BaseModel):
    id: str
    app_id: str
    name: str
    email: str
    status: str
    plan: str
    document_count: int = 0
    query_count: int = 0


@router.get("/apps/{app_id}/clients", response_model=List[ClientResponse])
async def list_clients(app_id: str):
    # Demo data
    return [
        ClientResponse(
            id="acme-corp",
            app_id=app_id,
            name="Acme Corporation",
            email="admin@acme.com",
            status="active",
            plan="enterprise",
            document_count=234,
            query_count=15420
        )
    ]


@router.post("/apps/{app_id}/clients")
async def create_client(app_id: str, client: ClientCreate):
    return {
        "id": client.id,
        "app_id": app_id,
        "api_key": f"bb_client_{app_id}_{client.id}_demo_key_abc"
    }