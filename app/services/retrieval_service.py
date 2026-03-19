"""
Vector retrieval service for RAG using Qdrant
"""
from typing import List, Optional
from app.core.config import settings


class RetrievalService:
    """Handles vector similarity search in Qdrant"""
    
    def __init__(self):
        self.collection_name = "blackbox_embeddings"
        self._client = None
    
    @property
    def client(self):
        """Lazy load Qdrant client"""
        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(url=settings.qdrant_url)
        return self._client
    
    async def search(
        self,
        query_vector: List[float],
        scope: str,
        top_k: int = 8,
        score_threshold: float = 0.5
    ) -> List[dict]:
        """
        Search for similar vectors in Qdrant
        
        Args:
            query_vector: Query embedding vector
            scope: Tenant scope filter (app_id::client_id)
            top_k: Number of results to return
            score_threshold: Minimum similarity score
        
        Returns:
            List of search results with metadata
        """
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter={
                    "must": [
                        {
                            "key": "scope",
                            "match": {"value": scope}
                        }
                    ]
                },
                limit=top_k,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for hit in search_result:
                results.append({
                    "id": str(hit.id),
                    "score": hit.score,
                    "text": hit.payload.get("text", ""),
                    "metadata": hit.payload
                })
            
            return results
        except Exception as e:
            print(f"Qdrant search error: {e}")
            return []
    
    async def insert(
        self,
        vectors: List[List[float]],
        payloads: List[dict],
        ids: List[str]
    ) -> bool:
        """
        Insert vectors into Qdrant
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata dicts
            ids: List of point IDs
        
        Returns:
            True if successful
        """
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    {
                        "id": ids[i],
                        "vector": vectors[i],
                        "payload": payloads[i]
                    }
                    for i in range(len(vectors))
                ]
            )
            return True
        except Exception as e:
            print(f"Qdrant insert error: {e}")
            return False
    
    async def delete_by_scope(self, scope: str) -> bool:
        """
        Delete all vectors for a scope
        
        Args:
            scope: Tenant scope
        
        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector={
                    "must": [
                        {
                            "key": "scope",
                            "match": {"value": scope}
                        }
                    ]
                }
            )
            return True
        except Exception as e:
            print(f"Qdrant delete error: {e}")
            return False
    
    async def get_count(self, scope: Optional[str] = None) -> int:
        """
        Get count of vectors in collection
        
        Args:
            scope: Optional scope filter
        
        Returns:
            Number of vectors
        """
        try:
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter={
                    "must": [
                        {
                            "key": "scope",
                            "match": {"value": scope}
                        }
                    ]
                } if scope else None
            )
            return result.count
        except Exception as e:
            print(f"Qdrant count error: {e}")
            return 0


# Global instance
retrieval_service = RetrievalService()