import pytest
from math_tutor.utils.long_term_memory import LongTermMemory

def test_memory_operations():
    memory = LongTermMemory("test_student")
    
    # Test ajout
    memory.add_memory(
        content="Test content",
        metadata={"type": "test"}
    )
    
    # Test récupération
    memories = memory.retrieve_related_memories("test")
    assert len(memories) > 0
    assert "Test content" in memories[0].content