"""
Text embedding service for RAG
"""
from typing import List
import httpx
import hashlib
from app.core.config import settings


class EmbeddingService:
    """Handles text embeddings using LLM providers"""
    
    def __init__(self):
        self.client = None
    
    async def embed_text(
        self, 
        text: str | List[str],
        provider: str = "openai",
        model: str = "text-embedding-3-small"
    ) -> List[List[float]]:
        """
        Generate embeddings for text(s)
        
        Args:
            text: Single text or list of texts
            provider: Provider to use (openai, anthropic, etc.)
            model: Model identifier
        
        Returns:
            List of embedding vectors
        """
        if isinstance(text, str):
            text = [text]
        
        # For now, use OpenAI-style API format
        # Can be extended to support other providers
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.qdrant_url}/collections/blackbox_embeddings/points",
                    json={
                        "points": [
                            {
                                "id": hash(text[i]),
                                "vector": await self._get_embedding(text[i]),
                                "payload": {"text": text[i]}
                            }
                            for i in range(len(text))
                        ]
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            # Fallback: Return simple hash-based embeddings for demo
            print(f"Embedding error: {e}, using fallback")
            return [self._simple_hash_embedding(t) for t in text]
    
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding from LLM provider
        """
        # Demo: Simple hash-based embedding
        # In production, this would call OpenAI, Anthropic, etc.
        return self._simple_hash_embedding(text)
    
    def _simple_hash_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """
        Simple hash-based embedding for demo purposes
        NOT FOR PRODUCTION - replace with real embeddings
        """
        # Create a deterministic pseudo-random vector from text
        import hashlib
        hash_val = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to float values
        values = []
        for i in range(0, len(hash_val), 2):
            hex_pair = hash_val[i:i+2]
            if len(hex_pair) == 2:
                float_val = int(hex_pair, 16) / 255.0
                values.append(float_val)
        
        # Pad or truncate to desired dimension
        while len(values) < dim:
            values.append(0.0)
        return values[:dim]
    
    async def create_collection(self):
        """Create Qdrant collection for embeddings"""
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url=settings.qdrant_url)
        
        # Check if collection exists
        try:
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if "blackbox_embeddings" not in collection_names:
                client.create_collection(
                    collection_name="blackbox_embeddings",
                    vectors_config={
                        "size": 1536,  # OpenAI embedding dimension
                        "distance": "Cosine"
                    }
                )
                print("Created Qdrant collection: blackbox_embeddings")
        except Exception as e:
            print(f"Qdrant collection error: {e}")


# Global instance
embedding_service = EmbeddingService()