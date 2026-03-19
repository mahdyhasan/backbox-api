"""
LLM Router Service
Implements the configuration cascade: client -> app -> platform
"""
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from typing import Optional, Dict, Any
from app.models.database import async_session
from app.models.models import Provider, Model, App, Client, AppAllowedProvider
from app.services.llm_providers import get_provider, LLMProvider


class LLMRouter:
    """Routes requests to the appropriate LLM provider/model"""
    
    # Cache provider instances
    _provider_cache: Dict[str, LLMProvider] = {}
    
    @staticmethod
    async def resolve_model(
        app_id: str,
        client_id: Optional[str] = None,
        task_type: str = "chat"
    ) -> tuple[str, LLMProvider, Model]:
        """
        Resolve the appropriate model using the cascade:
        1. Client-specific override
        2. App default configuration
        3. Platform default
        
        Returns: (model_identifier, provider_instance, model_data)
        """
        async with async_session() as session:
            # Get app configuration
            app_result = await session.execute(
                select(App).where(App.id == app_id)
            )
            app = app_result.scalar_one_or_none()
            
            if not app:
                raise ValueError(f"App not found: {app_id}")
            
            settings = app.settings or {}
            default_model = settings.get("default_model")
            task_overrides = settings.get("task_model_overrides", {})
            
            # Check client-specific override
            if client_id:
                client_result = await session.execute(
                    select(Client).where(Client.id == client_id)
                )
                client = client_result.scalar_one_or_none()
                
                if client:
                    client_settings = settings.get("client_settings", {}).get(str(client_id), {})
                    if "default_model" in client_settings:
                        default_model = client_settings["default_model"]
                    if "task_model_overrides" in client_settings:
                        task_overrides.update(client_settings["task_model_overrides"])
            
            # Resolve model identifier
            model_identifier = task_overrides.get(task_type, default_model)
            
            if not model_identifier:
                # Use platform default
                model_identifier = "claude-sonnet-4-20250514"  # Platform default
            
            # Get model details from database
            model_result = await session.execute(
                select(Model)
                .options(joinedload(Model.provider))
                .where(Model.identifier == model_identifier, Model.is_active == True)
            )
            model = model_result.scalar_one_or_none()
            
            if not model:
                # Fallback to first available model
                model_result = await session.execute(
                    select(Model)
                    .options(joinedload(Model.provider))
                    .join(Provider)
                    .join(AppAllowedProvider, and_(
                        AppAllowedProvider.provider_id == Provider.id,
                        AppAllowedProvider.app_id == app_id
                    ))
                    .where(Model.is_active == True, Provider.status == "active")
                    .limit(1)
                )
                model = model_result.scalar_one_or_none()
                
                if not model:
                    raise ValueError("No available models for this app")
            
            # Get provider instance (cached)
            provider_key = f"{model.provider.id}"
            if provider_key not in LLMRouter._provider_cache:
                LLMRouter._provider_cache[provider_key] = get_provider(
                    model.provider.name,
                    model.provider.api_key_encrypted or "",
                    model.provider.base_url
                )
            
            provider = LLMRouter._provider_cache[provider_key]
            
            return model.identifier, provider, model
    
    @staticmethod
    async def generate(
        app_id: str,
        client_id: Optional[str],
        messages: list,
        task_type: str = "chat",
        stream: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ):
        """
        Route and execute a generation request
        
        Returns: (response_text, input_tokens, output_tokens, cost_usd)
        """
        # Resolve model and provider
        model_id, provider, model = await LLMRouter.resolve_model(
            app_id, client_id, task_type
        )
        
        # Count input tokens
        input_text = "\n".join([msg["content"] for msg in messages])
        input_tokens = await provider.count_tokens(input_text, model_id)
        
        # Generate response
        if stream:
            # For streaming, we need to yield tokens as they come
            async def stream_with_cost():
                output_text = ""
                output_tokens = 0
                async for chunk in provider.generate(
                    model_id, messages, max_tokens, temperature, stream=True
                ):
                    output_text += chunk
                    output_tokens += 1  # Approximate
                    yield chunk
                
                # Calculate cost
                input_cost = (input_tokens / 1000) * float(model.input_cost_per_1k)
                output_cost = (output_tokens / 1000) * float(model.output_cost_per_1k)
                total_cost = input_cost + output_cost
                
                # Log usage
                await LLMRouter._log_usage(
                    app_id, client_id, provider.id, model.id,
                    "generate", input_tokens, output_tokens, total_cost
                )
            
            return stream_with_cost()
        else:
            # Non-streaming
            response_text = await provider.generate(
                model_id, messages, max_tokens, temperature, stream=False
            )
            
            # Count output tokens
            output_tokens = await provider.count_tokens(response_text, model_id)
            
            # Calculate cost
            input_cost = (input_tokens / 1000) * float(model.input_cost_per_1k)
            output_cost = (output_tokens / 1000) * float(model.output_cost_per_1k)
            total_cost = input_cost + output_cost
            
            # Log usage
            await LLMRouter._log_usage(
                app_id, client_id, provider.id, model.id,
                "generate", input_tokens, output_tokens, total_cost
            )
            
            return {
                "response": response_text,
                "model_used": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": total_cost,
                "provider": model.provider.name
            }
    
    @staticmethod
    async def _log_usage(
        app_id: str,
        client_id: Optional[str],
        provider_id: str,
        model_id: str,
        request_type: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """Log usage to database"""
        from app.models.models import UsageLog
        import uuid
        
        async with async_session() as session:
            log = UsageLog(
                id=uuid.uuid4(),
                app_id=app_id,
                client_id=client_id,
                provider_id=provider_id,
                model_id=model_id,
                request_type=request_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=cost_usd,
                status_code=200
            )
            session.add(log)
            await session.commit()
    
    @staticmethod
    def clear_cache():
        """Clear provider cache (useful for testing)"""
        LLMRouter._provider_cache.clear()