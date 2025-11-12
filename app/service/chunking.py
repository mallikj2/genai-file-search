from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
from app.config import settings
import tiktoken

class ChunkingService:
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self._token_length,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _token_length(self, text: str) -> int:
        """Calculate token length using tiktoken"""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Split text into chunks with metadata
        
        Args:
            text: Text to chunk
            metadata: Additional metadata (page_number, etc.)
        
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        chunks = self.text_splitter.split_text(text)
        
        result = []
        for idx, chunk in enumerate(chunks):
            chunk_dict = {
                "chunk_index": idx,
                "text": chunk,
                "token_count": self._token_length(chunk)
            }
            
            if metadata:
                chunk_dict.update(metadata)
            
            result.append(chunk_dict)
        
        return result
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Chunk multiple documents
        
        Args:
            documents: List of document dictionaries with 'text' and 'metadata'
        
        Returns:
            List of all chunks with document metadata
        """
        all_chunks = []
        
        for doc in documents:
            text = doc.get("text", "")
            doc_metadata = doc.get("metadata", {})
            
            chunks = self.chunk_text(text, doc_metadata)
            all_chunks.extend(chunks)
        
        return all_chunks

chunking_service = ChunkingService()
