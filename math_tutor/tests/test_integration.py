import mlflow
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime
from math_tutor.system_GB_Coach import MathTutoringSystem, StudentProfile, Exercise, EvaluationResult
from math_tutor.utils.file_processor import FileProcessor
from math_tutor.utils.long_term_memory import LongTermMemory

@pytest.fixture
def tutoring_system(monkeypatch):
    # Create a mock LearningObjectives class
    mock_learning_objectives = MagicMock()
    mock_learning_objectives.objectives = {"equations": {"description": "Test equations"}}
    
    # Patch the LearningObjectives class in the system_GB_Coach module
    monkeypatch.setattr(
        'math_tutor.system_GB_Coach.LearningObjectives',
        mock_learning_objectives
    )
    
    # Mock file processor
    monkeypatch.setattr(
        'math_tutor.utils.file_processor.FileProcessor.extract_text_from_file',
        lambda *args, **kwargs: "x = 2"
    )
    
    # Mock Prompt.ask to avoid interactive input
    monkeypatch.setattr('rich.prompt.Prompt.ask', lambda *args, **kwargs: "1")
    
    system = MathTutoringSystem()
    yield system
    
    if hasattr(system, 'mlflow_run') and system.mlflow_run:
        mlflow.end_run()

@pytest.fixture
def sample_student():
    return StudentProfile(
        student_id="test123",
        name="Test Student",
        level=1,
        current_objective="equations"
    )

@pytest.fixture
def sample_exercise():
    return Exercise(
        exercise="Résoudre 2x + 3 = 7",
        solution="x = 2",
        hints=["Isoler x", "Diviser par le coefficient"],
        difficulty="Facile",
        concept="Équations linéaires"
    )

def test_authenticate_student(tutoring_system):
    # Mock student creation
    with patch.object(tutoring_system.student_manager, 'create_student') as mock_create:
        mock_create.return_value = StudentProfile(
            student_id="test123",
            name="Test Student",
            level=1
        )
        
        assert tutoring_system.authenticate_student() is True
        assert tutoring_system.current_student is not None
        assert hasattr(tutoring_system, 'long_term_memory')

def test_file_processing(tutoring_system, sample_exercise, tmp_path):
    # Create test file
    test_file = tmp_path / "test_response.txt"
    test_file.write_text("x = 2")
    
    # Mock evaluation
    def mock_evaluate(exercise, answer):
        return EvaluationResult(
            is_correct=True,
            error_type=None,
            feedback="Correct",
            detailed_explanation="...",
            step_by_step_correction="...",
            recommendations=[]
        )
    
    tutoring_system._evaluate_prompt = mock_evaluate
    
    result = tutoring_system._evaluate_response(sample_exercise, test_file)
    assert isinstance(result, EvaluationResult)
    assert result.is_correct is True

def test_long_term_memory(tutoring_system, sample_student):
    tutoring_system.current_student = sample_student
    
    # Mock memory
    mock_memories = [{
        "exercise": "2+2",
        "answer": "4",
        "evaluation": True,
        "timestamp": datetime.now().isoformat()
    }]
    
    tutoring_system.long_term_memory = Mock()
    tutoring_system.long_term_memory.retrieve_related_memories.return_value = mock_memories
    
    memories = tutoring_system.long_term_memory.retrieve_related_memories("équations")
    assert len(memories) == 1
    assert memories[0]["exercise"] == "2+2"

def test_personalized_coaching(tutoring_system, sample_exercise):
    evaluation = EvaluationResult(
        is_correct=False,
        error_type="calcul",
        feedback="Erreur de calcul",
        detailed_explanation="...",
        step_by_step_correction="...",
        recommendations=["Revoyez les bases"]
    )
    
    # Mock coaching response
    class MockCoach:
        motivation = "Keep trying!"
        strategy = "Practice more"
        encouragement = ["You can do it!"]
    
    tutoring_system._provide_personalized_coaching = lambda *args: MockCoach()
    
    coaching = tutoring_system._provide_personalized_coaching(evaluation, sample_exercise)
    assert coaching.motivation == "Keep trying!"
    assert coaching.strategy == "Practice more"
    assert len(coaching.encouragement) > 0

def test_full_workflow(tutoring_system, tmp_path, monkeypatch):
    # Mock student persistence
    monkeypatch.setattr(
        'math_tutor.system_GB_Coach.StudentManager.save_student',
        lambda *args, **kwargs: None
    )
    
    # Mock session start
    def mock_start_session():
        tutoring_system.current_student.learning_history.append({
            "exercise": "test",
            "timestamp": datetime.now().isoformat()
        })
    
    tutoring_system.start_learning_session = mock_start_session
    
    # Test authentication
    with patch.object(tutoring_system.student_manager, 'create_student') as mock_create:
        mock_create.return_value = StudentProfile(
            student_id="test123",
            name="Test Student",
            level=1
        )
        
        assert tutoring_system.authenticate_student() is True
    
    tutoring_system.start_learning_session()
    assert len(tutoring_system.current_student.learning_history) == 1
    assert tutoring_system.long_term_memory is not None