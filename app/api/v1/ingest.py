from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.core.tenancy import resolve_tenant, get_scope

router = APIRouter()


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    client_id: str = Form(None),
    tenant: tuple = Depends(resolve_tenant)
):
    key_type, app_id, token_client_id = tenant
    
    if key_type == "platform":
        raise HTTPException(400, "Platform key cannot ingest directly")
    
    if key_type == "app" and not client_id:
        raise HTTPException(400, "client_id required with App Key")
    
    final_client_id = token_client_id or client_id
    scope = get_scope(app_id, final_client_id)
    
    # TODO: Queue to Celery worker for processing
    
    return {
        "job_id": "demo-job-123",
        "status": "processing",
        "scope": scope,
        "filename": file.filename,
        "estimated_seconds": 30
    }