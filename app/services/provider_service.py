"""
Service for managing LLM providers and models
"""
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.database import async_session
from app.models.models import Provider, Model, App, AppAllowedProvider, ClientAssignedProvider, Client


class ProviderService:
    """Service for provider operations"""
    
    @staticmethod
    async def get_all_providers() -> List[dict]:
        """Get all providers with their models"""
        async with async_session() as session:
            result = await session.execute(
                select(Provider)
                .options(selectinload(Provider.models))
                .order_by(Provider.name)
            )
            providers = result.scalars().all()
            
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "display_name": p.display_name,
                    "base_url": p.base_url,
                    "status": p.status,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                    "models": [
                        {
                            "id": str(m.id),
                            "name": m.name,
                            "identifier": m.identifier,
                            "context_window": m.context_window,
                            "input_cost_per_1k": float(m.input_cost_per_1k),
                            "output_cost_per_1k": float(m.output_cost_per_1k),
                            "is_active": m.is_active,
                        }
                        for m in p.models
                    ],
                    "has_api_key": bool(p.api_key_encrypted),
                }
                for p in providers
            ]
    
    @staticmethod
    async def get_provider_by_id(provider_id: str) -> Optional[dict]:
        """Get a specific provider by ID"""
        async with async_session() as session:
            result = await session.execute(
                select(Provider)
                .options(selectinload(Provider.models))
                .where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                return None
            
            return {
                "id": str(provider.id),
                "name": provider.name,
                "display_name": provider.display_name,
                "base_url": provider.base_url,
                "status": provider.status,
                "api_key_encrypted": "****",  # Never return actual key
                "created_at": provider.created_at.isoformat(),
                "updated_at": provider.updated_at.isoformat(),
                "models": [
                    {
                        "id": str(m.id),
                        "name": m.name,
                        "identifier": m.identifier,
                        "context_window": m.context_window,
                        "input_cost_per_1k": float(m.input_cost_per_1k),
                        "output_cost_per_1k": float(m.output_cost_per_1k),
                        "is_active": m.is_active,
                    }
                    for m in provider.models
                ],
            }
    
    @staticmethod
    async def create_provider(data: dict) -> dict:
        """Create a new provider"""
        async with async_session() as session:
            provider = Provider(
                name=data["name"],
                display_name=data.get("display_name"),
                base_url=data.get("base_url"),
                api_key_encrypted=data.get("api_key"),  # In production, encrypt this!
                status=data.get("status", "active"),
            )
            session.add(provider)
            await session.commit()
            await session.refresh(provider)
            
            return {
                "id": str(provider.id),
                "name": provider.name,
                "display_name": provider.display_name,
                "base_url": provider.base_url,
                "status": provider.status,
                "created_at": provider.created_at.isoformat(),
            }
    
    @staticmethod
    async def update_provider(provider_id: str, data: dict) -> Optional[dict]:
        """Update a provider"""
        async with async_session() as session:
            result = await session.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                return None
            
            if "display_name" in data:
                provider.display_name = data["display_name"]
            if "base_url" in data:
                provider.base_url = data["base_url"]
            if "api_key" in data:
                provider.api_key_encrypted = data["api_key"]  # In production, encrypt this!
            if "status" in data:
                provider.status = data["status"]
            
            await session.commit()
            await session.refresh(provider)
            
            return {
                "id": str(provider.id),
                "name": provider.name,
                "display_name": provider.display_name,
                "base_url": provider.base_url,
                "status": provider.status,
                "updated_at": provider.updated_at.isoformat(),
            }
    
    @staticmethod
    async def delete_provider(provider_id: str) -> bool:
        """Delete a provider (cascades to models)"""
        async with async_session() as session:
            result = await session.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                return False
            
            await session.delete(provider)
            await session.commit()
            return True
    
    @staticmethod
    async def add_model(provider_id: str, data: dict) -> Optional[dict]:
        """Add a model to a provider"""
        async with async_session() as session:
            result = await session.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider:
                return None
            
            model = Model(
                provider_id=provider_id,
                name=data["name"],
                identifier=data["identifier"],
                context_window=data.get("context_window"),
                input_cost_per_1k=data.get("input_cost_per_1k", 0.0),
                output_cost_per_1k=data.get("output_cost_per_1k", 0.0),
                is_active=data.get("is_active", True),
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            
            return {
                "id": str(model.id),
                "name": model.name,
                "identifier": model.identifier,
                "context_window": model.context_window,
                "input_cost_per_1k": float(model.input_cost_per_1k),
                "output_cost_per_1k": float(model.output_cost_per_1k),
                "is_active": model.is_active,
            }
    
    @staticmethod
    async def get_app_providers(app_id: str) -> List[dict]:
        """Get providers allowed for a specific app"""
        async with async_session() as session:
            result = await session.execute(
                select(AppAllowedProvider)
                .options(selectinload(AppAllowedProvider.provider).selectinload(Provider.models))
                .where(AppAllowedProvider.app_id == app_id)
            )
            assignments = result.scalars().all()
            
            return [
                {
                    "app_id": assignment.app_id,
                    "provider_id": str(assignment.provider_id),
                    "provider_name": assignment.provider.name,
                    "display_name": assignment.provider.display_name,
                    "status": assignment.provider.status,
                    "daily_token_limit": assignment.daily_token_limit,
                    "models": [
                        {
                            "id": str(m.id),
                            "name": m.name,
                            "identifier": m.identifier,
                        }
                        for m in assignment.provider.models
                        if m.is_active
                    ],
                }
                for assignment in assignments
            ]
    
    @staticmethod
    async def assign_provider_to_app(app_id: str, provider_id: str, daily_token_limit: int = 100000) -> bool:
        """Assign a provider to an app"""
        async with async_session() as session:
            # Check if provider exists
            provider_result = await session.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = provider_result.scalar_one_or_none()
            if not provider:
                return False
            
            # Check if app exists
            app_result = await session.execute(
                select(App).where(App.id == app_id)
            )
            app = app_result.scalar_one_or_none()
            if not app:
                return False
            
            # Check if already assigned
            existing = await session.execute(
                select(AppAllowedProvider).where(
                    AppAllowedProvider.app_id == app_id,
                    AppAllowedProvider.provider_id == provider_id
                )
            )
            if existing.scalar_one_or_none():
                # Update existing
                await session.execute(
                    update(AppAllowedProvider)
                    .where(
                        AppAllowedProvider.app_id == app_id,
                        AppAllowedProvider.provider_id == provider_id
                    )
                    .values(daily_token_limit=daily_token_limit)
                )
            else:
                # Create new assignment
                assignment = AppAllowedProvider(
                    app_id=app_id,
                    provider_id=provider_id,
                    daily_token_limit=daily_token_limit
                )
                session.add(assignment)
            
            await session.commit()
            return True
    
    @staticmethod
    async def remove_provider_from_app(app_id: str, provider_id: str) -> bool:
        """Remove a provider from an app"""
        async with async_session() as session:
            result = await session.execute(
                delete(AppAllowedProvider).where(
                    AppAllowedProvider.app_id == app_id,
                    AppAllowedProvider.provider_id == provider_id
                )
            )
            await session.commit()
            return result.rowcount > 0