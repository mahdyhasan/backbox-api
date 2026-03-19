"""
Provider Management API (v2)
Allows Super Admin to manage LLM providers and models
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from app.core.tenancy import resolve_tenant
from app.services.provider_service import ProviderService

router = APIRouter()


# Pydantic Models
class ProviderCreate(BaseModel):
    name: str = Field(..., description="Unique provider identifier (e.g., 'anthropic')")
    display_name: str = Field(..., description="Display name (e.g., 'Anthropic Claude')")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key for the provider")
    status: str = Field(default="active", description="Provider status")


class ProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    status: Optional[str] = None


class ModelCreate(BaseModel):
    name: str = Field(..., description="Model display name")
    identifier: str = Field(..., description="API model identifier")
    context_window: Optional[int] = Field(default=8192, description="Context window size")
    input_cost_per_1k: float = Field(default=0.0, description="Cost per 1K input tokens")
    output_cost_per_1k: float = Field(default=0.0, description="Cost per 1K output tokens")
    is_active: bool = Field(default=True, description="Whether model is active")


class AssignProviderToApp(BaseModel):
    provider_id: str
    daily_token_limit: int = Field(default=100000, description="Daily token limit")


# Platform Admin Required
def require_platform_key(tenant: tuple = Depends(resolve_tenant)):
    key_type, _, _ = tenant
    if key_type != "platform":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform key required for provider management"
        )
    return tenant


# GET all providers
@router.get("/providers", response_model=List[dict])
async def list_providers(tenant: tuple = Depends(require_platform_key)):
    """List all LLM providers with their models"""
    return await ProviderService.get_all_providers()


# GET single provider
@router.get("/providers/{provider_id}", response_model=dict)
async def get_provider(provider_id: str, tenant: tuple = Depends(require_platform_key)):
    """Get a specific provider by ID"""
    provider = await ProviderService.get_provider_by_id(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return provider


# POST create provider
@router.post("/providers", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_provider(provider: ProviderCreate, tenant: tuple = Depends(require_platform_key)):
    """Create a new LLM provider"""
    try:
        result = await ProviderService.create_provider(provider.model_dump())
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create provider: {str(e)}"
        )


# PATCH update provider
@router.patch("/providers/{provider_id}", response_model=dict)
async def update_provider(
    provider_id: str,
    provider: ProviderUpdate,
    tenant: tuple = Depends(require_platform_key)
):
    """Update a provider (name cannot be changed)"""
    result = await ProviderService.update_provider(
        provider_id,
        provider.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return result


# DELETE provider
@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: str, tenant: tuple = Depends(require_platform_key)):
    """Delete a provider (cascades to models and assignments)"""
    success = await ProviderService.delete_provider(provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return None


# POST add model to provider
@router.post("/providers/{provider_id}/models", status_code=status.HTTP_201_CREATED, response_model=dict)
async def add_model(
    provider_id: str,
    model: ModelCreate,
    tenant: tuple = Depends(require_platform_key)
):
    """Add a model to a provider"""
    result = await ProviderService.add_model(provider_id, model.model_dump())
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return result


# GET app providers
@router.get("/apps/{app_id}/providers", response_model=List[dict])
async def get_app_providers(app_id: str, tenant: tuple = Depends(require_platform_key)):
    """Get providers assigned to a specific app"""
    return await ProviderService.get_app_providers(app_id)


# POST assign provider to app
@router.post("/apps/{app_id}/providers", status_code=status.HTTP_201_CREATED)
async def assign_provider_to_app(
    app_id: str,
    assignment: AssignProviderToApp,
    tenant: tuple = Depends(require_platform_key)
):
    """Assign a provider to an app"""
    success = await ProviderService.assign_provider_to_app(
        app_id,
        assignment.provider_id,
        assignment.daily_token_limit
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign provider (app or provider not found)"
        )
    return {
        "app_id": app_id,
        "provider_id": assignment.provider_id,
        "status": "assigned",
        "daily_token_limit": assignment.daily_token_limit
    }


# DELETE remove provider from app
@router.delete("/apps/{app_id}/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_provider_from_app(
    app_id: str,
    provider_id: str,
    tenant: tuple = Depends(require_platform_key)
):
    """Remove a provider from an app"""
    success = await ProviderService.remove_provider_from_app(app_id, provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    return None