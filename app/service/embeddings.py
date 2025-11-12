import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
from app.config import settings
from loguru import logger
import uuid

class VectorStoreService:
    """Manage ChromaDB operations for vector storage and retrieval"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure the collection exists"""
        try:
            self.collection = self.client.get_collection(
                name=settings.CHROMA_COLLECTION_NAME
            )
        except:
            self.collection = self.client.create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
    
    def add_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict]
    ) -> bool:
        """
        Add chunks to vector store
        
        Args:
            chunk_ids: List of unique chunk IDs
            texts: List of chunk texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
        
        Returns:
            Success status
        """
        try:
            self.collection.add(
                ids=chunk_ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Added {len(chunk_ids)} chunks to vector store")
            return True
        except Exception as e:
            logger.error(f"Error adding chunks to vector store: {e}")
            return False
    
    def search(
        self,
        query_embedding: List[float],
        category_id: int,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for similar chunks
        
        Args:
            query_embedding: Query embedding vector
            category_id: Filter by category ID
            top_k: Number of results to return
        
        Returns:
            List of matching chunks with metadata
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"category_id": category_id}
            )
            
            if not results or not results['ids'] or not results['ids'][0]:
                return []
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "chunk_id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else 0.0
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def delete_by_file_id(self, file_id: int) -> bool:
        """
        Delete all chunks for a specific file
        
        Args:
            file_id: File ID to delete chunks for
        
        Returns:
            Success status
        """
        try:
            self.collection.delete(
                where={"file_id": file_id}
            )
            logger.info(f"Deleted chunks for file_id: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return False
    
    def delete_by_category_id(self, category_id: int) -> bool:
        """
        Delete all chunks for a specific category
        
        Args:
            category_id: Category ID to delete chunks for
        
        Returns:
            Success status
        """
        try:
            self.collection.delete(
                where={"category_id": category_id}
            )
            logger.info(f"Deleted chunks for category_id: {category_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            return False
    
    def get_all_chunks_by_category(self, category_id: int) -> List[Dict]:
        """
        Get all chunks for a category
        
        Args:
            category_id: Category ID
        
        Returns:
            List of chunks
        """
        try:
            results = self.collection.get(
                where={"category_id": category_id}
            )
            
            if not results or not results['ids']:
                return []
            
            formatted_results = []
            for i in range(len(results['ids'])):
                formatted_results.append({
                    "chunk_id": results['ids'][i],
                    "text": results['documents'][i],
                    "metadata": results['metadatas'][i]
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error getting chunks: {e}")
            return []

vector_store_service = VectorStoreService()
