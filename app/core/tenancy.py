from fastapi import Request, HTTPException
from typing import Tuple, Optional


async def resolve_tenant(request: Request) -> Tuple[str, str, Optional[str]]:
    """
    Returns: (key_type, app_id, client_id)
    Platform Key: ('platform', '*', '*')
    App Key: ('app', 'aura', None) - client_id from body
    Client Key: ('client', 'aura', 'acme-corp')
    """
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    key = auth.replace("Bearer ", "")
    
    # Demo resolution - replace with DB lookup
    if key.startswith("bb_platform_"):
        return ("platform", "*", "*")
    elif key.startswith("bb_app_aura"):
        return ("app", "aura", None)
    elif key.startswith("bb_app_sales"):
        return ("app", "sales-analyzer", None)
    elif key.startswith("bb_client_"):
        # Extract client from key
        return ("client", "aura", "acme-corp")
    
    # Default demo
    return ("app", "demo", None)


def get_scope(app_id: str, client_id: Optional[str]) -> str:
    """Generate compound scope key for Qdrant filtering"""
    if client_id:
        return f"{app_id}::{client_id}"
    return app_id