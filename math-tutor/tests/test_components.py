# tests/test_components.py
def test_exercise_generation(tutoring_system):
    """Test la génération d'exercices"""
    tutoring_system.current_student = tutoring_system.student_manager.create_student("Test")
    tutoring_system.current_student.current_objective = list(
        tutoring_system.learning_objectives.objectives.keys()
    )[0]
    
    exercise = tutoring_system._generate_exercise()
    assert exercise['exercise']
    assert exercise['solution']
    assert exercise['difficulty']

def test_student_persistence(tutoring_system):
    """Test la persistance des données étudiant"""
    # Création
    student = tutoring_system.student_manager.create_student("Persistence Test")
    original_id = student.student_id
    
    # Rechargement
    loaded = tutoring_system.student_manager.load_student(original_id)
    assert loaded is not None
    assert loaded.student_id == original_id
    assert loaded.name == "Persistence Test"