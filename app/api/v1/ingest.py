"""
Document ingestion endpoint for RAG
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.core.tenancy import resolve_tenant, get_scope
from app.services.document_service import document_storage
from app.services.chunking_service import chunker
from app.services.embedding_service import embedding_service

router = APIRouter()


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    client_id: str = Form(None),
    tenant: tuple = Depends(resolve_tenant)
):
    """
    Ingest a document into RAG system
    
    Flow:
    1. Save file to storage
    2. Extract text from file
    3. Chunk text
    4. Generate embeddings
    5. Store in Qdrant
    6. Update database record
    """
    key_type, app_id, token_client_id = tenant
    
    # Validation
    if key_type == "platform":
        raise HTTPException(400, "Platform key cannot ingest directly")
    
    if key_type == "app" and not client_id:
        raise HTTPException(400, "client_id required with App Key")
    
    final_client_id = token_client_id or client_id
    scope = get_scope(app_id, final_client_id)
    
    # Step 1: Save file
    file_meta = await document_storage.save_upload(file, scope)
    
    # Step 2: Extract text (simplified - in production use unstructured)
    try:
        content = await file.read()
        if file.content_type == "application/pdf":
            # For PDF, just use filename as placeholder
            text = f"Document content from {file.filename}"
        elif file.content_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            text = f"Document content from {file.filename}"
        else:
            # Assume plain text
            text = content.decode('utf-8', errors='ignore')
    except Exception as e:
        raise HTTPException(500, f"Failed to extract text: {str(e)}")
    
    # Step 3: Chunk text
    chunks = chunker.chunk_by_structure(text)
    
    # Step 4: Generate embeddings
    chunk_texts = [chunk["text"] for chunk in chunks]
    
    # For demo, use simple hash embeddings
    # In production, this would call real embedding API
    vectors = []
    for chunk_text in chunk_texts:
        vectors.append(embedding_service._simple_hash_embedding(chunk_text))
    
    # Step 5: Prepare payloads with scope and metadata
    payloads = []
    ids = []
    for i, chunk in enumerate(chunks):
        payload = {
            "text": chunk["text"],
            "scope": scope,
            "app_id": app_id,
            "client_id": final_client_id,
            "filename": file.filename,
            "chunk_index": chunk["chunk_index"],
            "file_type": file_meta["file_type"]
        }
        payloads.append(payload)
        ids.append(f"{file_meta['id']}_{i}")
    
    # Step 6: Insert into Qdrant
    from app.services.retrieval_service import retrieval_service
    success = await retrieval_service.insert(vectors, payloads, ids)
    
    if not success:
        raise HTTPException(500, "Failed to store embeddings")
    
    return {
        "job_id": file_meta["id"],
        "status": "completed",
        "scope": scope,
        "filename": file.filename,
        "chunk_count": len(chunks),
        "message": "Document ingested successfully"
    }


@router.get("/documents")
async def list_documents(tenant: tuple = Depends(resolve_tenant)):
    """List all documents for a scope"""
    key_type, app_id, client_id = tenant
    scope = get_scope(app_id, client_id)
    
    from app.services.retrieval_service import retrieval_service
    count = await retrieval_service.get_count(scope)
    
    return {
        "scope": scope,
        "document_count": count // 10,  # Estimate (10 chunks per doc)
        "chunk_count": count
    }


@router.delete("/documents")
async def delete_documents(tenant: tuple = Depends(resolve_tenant)):
    """Delete all documents for a scope"""
    key_type, app_id, token_client_id = tenant
    
    if key_type == "platform":
        raise HTTPException(400, "Platform key cannot delete")
    
    client_id = token_client_id or "*"
    scope = get_scope(app_id, client_id)
    
    from app.services.retrieval_service import retrieval_service
    success = await retrieval_service.delete_by_scope(scope)
    
    if not success:
        raise HTTPException(500, "Failed to delete documents")
    
    return {
        "status": "deleted",
        "scope": scope,
        "message": f"All documents deleted for {scope}"
    }