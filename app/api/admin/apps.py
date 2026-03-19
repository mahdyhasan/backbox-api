from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.tenancy import resolve_tenant

router = APIRouter()


class AppCreate(BaseModel):
    id: str
    name: str
    display_name: str


class AppResponse(BaseModel):
    id: str
    name: str
    display_name: str
    status: str
    client_count: int = 0


@router.get("/apps", response_model=List[AppResponse])
async def list_apps(tenant: tuple = Depends(resolve_tenant)):
    key_type, _, _ = tenant
    if key_type != "platform":
        raise HTTPException(403, "Platform key required")
    
    # Demo data
    return [
        AppResponse(id="aura", name="aura", display_name="AURA AI Chatbot", status="active", client_count=47),
        AppResponse(id="sales-analyzer", name="sales-analyzer", display_name="Sales Call Analyzer", status="active", client_count=12),
    ]


@router.post("/apps")
async def create_app(app: AppCreate, tenant: tuple = Depends(resolve_tenant)):
    key_type, _, _ = tenant
    if key_type != "platform":
        raise HTTPException(403, "Platform key required")
    
    return {"id": app.id, "status": "created", "api_key": f"bb_app_{app.id}_demo_key_xyz"}