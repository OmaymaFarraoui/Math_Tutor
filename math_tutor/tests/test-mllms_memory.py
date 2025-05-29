from pathlib import Path
import pytest
from unittest.mock import Mock
from math_tutor.system_GB_Coach import MathTutoringSystem ,Exercise, EvaluationResult


@pytest.fixture
def mock_system(monkeypatch):
    # Create system instance
    system = MathTutoringSystem()
    
    # Mock authentication to avoid user input
    monkeypatch.setattr('rich.prompt.Prompt.ask', lambda *args, **kwargs: "1")
    
    # Mock student profile
    system.current_student = Mock()
    system.current_student.current_objective = "algebra"
    
    # Mock exercise generation
    def mock_generate_exercise():
        return Exercise(
            exercise="Solve 2x + 3 = 7",
            solution="x = 2",
            hints=["Subtract 3 from both sides", "Divide by 2"],
            difficulty="easy",
            concept="linear equations"
        )
    system._generate_exercise = mock_generate_exercise
    
    # Mock evaluation
    def mock_evaluate(exercise, answer):
        return EvaluationResult(
            is_correct=True,
            error_type=None,
            feedback="Good job!",
            detailed_explanation="You solved it correctly",
            step_by_step_correction="",
            recommendations=[]
        )
    system._evaluate_prompt = mock_evaluate
    
    # Mock file processor
    system.file_processor = Mock()
    system.file_processor.extract_text_from_file.return_value = "x = 2"
    
    # Mock long term memory
    system.long_term_memory = Mock()
    system.long_term_memory.retrieve_related_memories.return_value = [
        {"content": "Previous equation solving example"}
    ]
    
    return system

def test_mllms_memory(mock_system):
    # 1. Generate exercise
    exercise = mock_system._generate_exercise()
    assert exercise is not None
    assert isinstance(exercise, Exercise)
    
    # 2. Evaluate text response
    evaluation_text = mock_system._evaluate_response(exercise, "Ma réponse textuelle")
    assert evaluation_text is not None
    assert evaluation_text.is_correct is True
    
    # 3. Evaluate image response
    image_path = Path("D:\M2 OF\STAGE PFE\screen\test.png")  
    evaluation_img = mock_system._evaluate_response(exercise, str(image_path))
    assert evaluation_img is not None
    
    # 4. Test memory retrieval
    memories = mock_system.long_term_memory.retrieve_related_memories("équations du second degré")
    assert isinstance(memories, list)
    assert len(memories) > 0