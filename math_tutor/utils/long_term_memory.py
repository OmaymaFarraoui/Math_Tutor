# utils/long_term_memory.py
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class MemoryItem(BaseModel):
    content: str
    metadata: Dict[str, str]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class LongTermMemory:
    def __init__(self, collection_name: str, client: Optional[chromadb.Client] = None):
        self.collection_name = collection_name
        try:
            self.client = client or chromadb.PersistentClient(
                path="memory_db",
                settings=chromadb.Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory="memory_db"
                )
            )
            
            self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_func,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Test immédiat de la connexion
            if not self.test_connection():
                raise ConnectionError("La connexion à la collection a échoué")
                
        except Exception as e:
            print(f"⚠️ Erreur initialisation mémoire: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Vérifie que la connexion fonctionne"""
        try:
            # Vérification du client
            if not self.client.heartbeat():
                return False
                
            # Vérification de la collection
            self.collection.peek()
            return True
        except Exception as e:
            print(f"⚠️ Échec test connexion: {str(e)}")
            return False

    def upsert_memory(self, content: str, metadata: Dict[str, str], id: str) -> None:
        """Unifie l'ajout et la mise à jour"""
        if not self.test_connection():
            raise ConnectionError("Connexion mémoire non disponible")
            
        try:
            existing = self.collection.get(ids=[id])
            if existing['ids']:
                self.collection.update(
                    documents=[content],
                    metadatas=[metadata],
                    ids=[id]
                )
            else:
                self.collection.add(
                    documents=[content],
                    metadatas=[metadata],
                    ids=[id]
                )
        except Exception as e:
            print(f"⚠️ Échec upsert mémoire: {str(e)}")
            raise

    
    def add_memory(self, content: str, metadata: Dict[str, str], id: Optional[str] = None) -> None:
        """Ajoute un souvenir à la mémoire avec ID optionnel"""
        memory_id = id or f"mem_{datetime.now().timestamp()}"
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[memory_id]
        )
    

    def retrieve_related_memories(self, query: str, n_results: int = 3) -> List[MemoryItem]:
        """Récupère des souvenirs pertinents"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        memories = []
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            memories.append(MemoryItem(
                content=doc,
                metadata=meta,
                timestamp=meta.get('timestamp', '')
            ))
        
        return memories
    
    def get_memory_timeline(self) -> List[MemoryItem]:
        """Récupère tous les souvenirs dans l'ordre chronologique"""
        all_memories = self.collection.get()
        memories = []
        
        for doc, meta, mem_id in zip(all_memories['documents'], all_memories['metadatas'], all_memories['ids']):
            memories.append(MemoryItem(
                content=doc,
                metadata=meta,
                timestamp=meta.get('timestamp', '')
            ))
        
        # Trier par timestamp
        memories.sort(key=lambda x: x.timestamp)
        return memories
