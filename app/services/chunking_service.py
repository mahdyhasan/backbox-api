"""
Document chunking service for RAG
"""
import re
from typing import List


class Chunker:
    """Splits documents into chunks for embedding"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[dict]:
        """
        Split text into chunks
        
        Args:
            text: Input text to chunk
        
        Returns:
            List of dicts with chunk data
        """
        # Clean text
        text = self._clean_text(text)
        
        if not text or len(text) < 100:
            return [{
                "text": text,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": len(text)
            }]
        
        # Split into chunks
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                
                # Prefer sentence break, then line break
                break_point = max(last_period, last_newline)
                if break_point > start:
                    end = break_point + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": len(chunks),
                    "start_char": start,
                    "end_char": end
                })
            
            # Move start position with overlap
            start = end - self.chunk_overlap
        
        return chunks
    
    def chunk_by_structure(self, text: str) -> List[dict]:
        """
        Split text by structure (paragraphs, headers)
        
        Args:
            text: Input text
        
        Returns:
            List of structured chunks
        """
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text.strip())
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If paragraph is too large, split it
            if para_size > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        "text": "\n\n".join(current_chunk),
                        "chunk_index": len(chunks),
                        "type": "paragraph"
                    })
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph
                sub_chunks = self.chunk_text(para)
                chunks.extend(sub_chunks)
                continue
            
            # Check if we should start new chunk
            if current_size + para_size > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        "text": "\n\n".join(current_chunk),
                        "chunk_index": len(chunks),
                        "type": "paragraph"
                    })
                current_chunk = []
                current_size = 0
            
            # Add paragraph to current chunk
            current_chunk.append(para)
            current_size += para_size
        
        # Add remaining paragraphs
        if current_chunk:
            chunks.append({
                "text": "\n\n".join(current_chunk),
                "chunk_index": len(chunks),
                "type": "paragraph"
            })
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive newlines
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        return text.strip()


# Global instance
chunker = Chunker(chunk_size=1000, chunk_overlap=200)