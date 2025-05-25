import pytest
from unittest.mock import patch, Mock
from math_tutor.system_GB_Coach import MathTutoringSystem
import json
from pathlib import Path

def test_full_workflow(tutoring_system, tmp_path):
    """Test complet du workflow d'apprentissage"""
    # 1. Test d'authentification étudiant
    with patch('rich.prompt.Prompt.ask', side_effect=["1", "Test Student"]):
        assert tutoring_system.authenticate_student() is True
        student = tutoring_system.current_student
        assert student.name == "Test Student"

    # 2. Vérification de l'objectif initial
    assert student.current_objective is not None
    assert student.level == 1

    # 3. Test de génération d'exercice
    exercise = tutoring_system._generate_exercise()
    assert exercise is not None
    assert len(exercise['hints']) > 0

    # 4. Test d'évaluation de réponse
    test_answer = "42"  # Réponse factice
    evaluation = tutoring_system._evaluate_response(exercise, test_answer)
    assert evaluation is not None
    assert isinstance(evaluation['feedback'], str)

    # 5. Test de coaching personnalisé
    coaching = tutoring_system._provide_personalized_coaching(evaluation, exercise)
    assert isinstance(coaching['motivation'], str)
    assert isinstance(coaching['strategy'], str)
    assert isinstance(coaching['tip'], str)
    assert isinstance(coaching['encouragement'], list)  # Changed to check for list
    assert all(isinstance(msg, str) for msg in coaching['encouragement'])  # Check all items are strings