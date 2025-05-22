import mlflow
import pytest
from your_module import MathTutoringSystem

def test_mlflow_tracking():
    """Teste que MLflow peut tracker des runs"""
    with mlflow.start_run():
        mlflow.log_param("test_param", 1)
        assert mlflow.active_run() is not None

def test_exercise_generation():
    """Teste la génération d'exercices avec tracking"""
    system = MathTutoringSystem()
    exercise = system._generate_exercise()
    assert exercise is not None
    if system.llm:  # Si le mode online est actif
        assert mlflow.last_active_run() is not None