import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from fastembed import TextEmbedding
from app.config import settings

logger = logging.getLogger(__name__)

# Global cache for FastEmbed model to avoid loading repeatedly
_fastembed_model = None

def get_fastembed_model():
    """Load FastEmbed model for local embeddings generation."""
    global _fastembed_model
    if _fastembed_model is None:
        logger.info("Initializing FastEmbed BAAI/bge-small-en-v1.5 model...")
        # BAAI/bge-small-en-v1.5 has 384 dimensions and is optimized for speed/accuracy
        _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _fastembed_model


class QdrantService:
    """
    Service wrapper for Qdrant Cloud or local in-memory vector storage.
    
    Why: Provides vector storage operations for semantic search and RAG.
    What: Creates collections, embeds texts via FastEmbed, and runs similarity queries.
    """
    _client = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        """Get or initialize the Qdrant Cloud client."""
        if cls._client is not None:
            return cls._client

        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            raise ValueError(
                "QDRANT_URL and QDRANT_API_KEY must be configured in environment settings to run Qdrant Cloud vector search."
            )

        logger.info(f"Connecting to Qdrant Cloud at {settings.QDRANT_URL}")
        cls._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        return cls._client

    @classmethod
    def get_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using FastEmbed."""
        model = get_fastembed_model()
        embeddings = list(model.embed(texts))
        # Convert numpy floats/arrays to standard Python lists
        return [list(map(float, emb)) for emb in embeddings]

    @classmethod
    def create_collection(cls, collection_name: str) -> bool:
        """Create a collection config with 384 dimensions and Cosine similarity metric."""
        client = cls.get_client()
        try:
            if client.collection_exists(collection_name):
                return True
                
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=384,
                    distance=qmodels.Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    @classmethod
    def upsert_chunks(cls, collection_name: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        Upsert a list of text chunks with generated embeddings into Qdrant.
        
        Inputs:
            - collection_name (str): Name of the destination collection.
            - chunks (List[Dict]): List of dicts, each with keys: 'id', 'content', and optional 'metadata'.
        Outputs:
            - bool: True if upsert succeeded, False otherwise.
        """
        client = cls.get_client()
        cls.create_collection(collection_name)
        
        try:
            texts = [c["content"] for c in chunks]
            embeddings = cls.get_embeddings(texts)
            
            points = []
            for idx, chunk in enumerate(chunks):
                point_id = str(chunk["id"])
                points.append(
                    qmodels.PointStruct(
                        id=point_id,
                        vector=embeddings[idx],
                        payload={
                            "content": chunk["content"],
                            **(chunk.get("metadata") or {})
                        }
                    )
                )
                
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Successfully upserted {len(points)} points into collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points into collection {collection_name}: {e}")
            return False

    @classmethod
    def search_similar(
        cls, collection_name: str, query: str, limit: int = 5, filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search against Qdrant collection using query embedding.
        
        Inputs:
            - collection_name (str): Collection name to query.
            - query (str): Text prompt to search for.
            - limit (int): Max number of matching chunks to return.
            - filter_dict (dict): Optional payload conditions.
        Outputs:
            - List[Dict]: Matches containing id, score, content, and metadata.
        """
        client = cls.get_client()
        if not client.collection_exists(collection_name):
            logger.warning(f"Collection {collection_name} does not exist. Returning empty results.")
            return []
            
        try:
            query_vector = cls.get_embeddings([query])[0]
            
            # Setup payload filtering conditions if provided
            qfilter = None
            if filter_dict:
                conditions = []
                for k, v in filter_dict.items():
                    conditions.append(
                        qmodels.FieldCondition(
                            key=k,
                            match=qmodels.MatchValue(value=v)
                        )
                    )
                qfilter = qmodels.Filter(must=conditions)
                
            response = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=qfilter,
                limit=limit
            )
            results = response.points
            
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.payload.get("content"),
                    "metadata": {k: v for k, v in hit.payload.items() if k != "content"}
                })
            return formatted_results
        except Exception as e:
            logger.error(f"Failed to perform semantic search in Qdrant: {e}")
            return []

    @classmethod
    def delete_points(cls, collection_name: str, point_ids: List[str]) -> bool:
        """Delete specific points from Qdrant by ID list."""
        client = cls.get_client()
        try:
            client.delete(
                collection_name=collection_name,
                points_selector=qmodels.PointIdsList(
                    points=point_ids
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete points from Qdrant: {e}")
            return False

    @classmethod
    def delete_collection(cls, collection_name: str) -> bool:
        """Drop a collection from Qdrant."""
        client = cls.get_client()
        try:
            client.delete_collection(collection_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False
