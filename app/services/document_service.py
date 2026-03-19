"""
Document storage service for handling file uploads
"""
import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException


class DocumentStorage:
    """Handles document storage (can be extended to S3)"""
    
    def __init__(self, storage_path: str = "/app/storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_upload(
        self, 
        file: UploadFile, 
        scope: str
    ) -> dict:
        """
        Save uploaded file to storage
        
        Args:
            file: Uploaded file
            scope: Tenant scope (app_id::client_id)
        
        Returns:
            dict with file metadata
        """
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}{file_ext}"
        
        # Create scope directory
        scope_path = self.storage_path / scope
        scope_path.mkdir(parents=True, exist_ok=True)
        
        file_path = scope_path / filename
        
        # Save file
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            raise HTTPException(500, f"Failed to save file: {str(e)}")
        
        return {
            "id": unique_id,
            "filename": file.filename,
            "storage_path": str(file_path),
            "file_size": len(content),
            "file_type": file.content_type or "application/octet-stream"
        }
    
    async def get_file(self, scope: str, file_id: str) -> Optional[bytes]:
        """Retrieve file content"""
        file_path = self.storage_path / scope / file_id
        if not file_path.exists():
            return None
        
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    def delete_file(self, scope: str, file_id: str) -> bool:
        """Delete file from storage"""
        file_path = self.storage_path / scope / file_id
        if file_path.exists():
            file_path.unlink()
            return True
        return False


# Global instance
document_storage = DocumentStorage()