# tests/test_components.py
from math_tutor.system_GB_Coach import MathTutoringSystem
import pytest

tutoring_system = MathTutoringSystem()

def test_exercise_generation():
    """Test la génération d'exercices"""
    # Create a test student
    tutoring_system.current_student = tutoring_system.student_manager.create_student("Test")
    
    # Verify there are learning objectives available
    objectives = list(tutoring_system.learning_objectives.objectives.keys())
    if not objectives:
        pytest.skip("No learning objectives available for testing")
    
    # Set the first objective
    tutoring_system.current_student.current_objective = objectives[0]
    
    # Generate exercise
    exercise = tutoring_system._generate_exercise()
    
    # Assertions
    assert exercise['exercise'], "Exercise text should not be empty"
    assert exercise['solution'], "Solution should not be empty"
    assert exercise['difficulty'], "Difficulty level should be set"

def test_student_persistence():
    """Test la persistance des données étudiant"""
    # Création
    student = tutoring_system.student_manager.create_student("Persistence Test")
    original_id = student.student_id
    
    # Rechargement
    loaded = tutoring_system.student_manager.load_student(original_id)
    assert loaded is not None
    assert loaded.student_id == original_id
    assert loaded.name == "Persistence Test"