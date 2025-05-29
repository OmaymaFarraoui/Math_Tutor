# utils/long_term_memory.py
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from pydantic import BaseModel, Field
import chromadb
from chromadb.utils import embedding_functions

class MemoryItem(BaseModel):
    content: str
    metadata: Dict[str, str]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class LongTermMemory:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.client = chromadb.PersistentClient(path="memory_db")
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name=f"student_{student_id}",
            embedding_function=self.embedding_func
        )
    
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