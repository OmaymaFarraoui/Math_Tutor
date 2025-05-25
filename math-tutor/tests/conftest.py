# tests/conftest.py
import pytest
from math_tutor.system_GB_Coach import MathTutoringSystem
from unittest.mock import patch # type: ignore
import mlflow

@pytest.fixture
def tutoring_system():
    """Fixture pour initialiser le système de tutorat"""
    with patch('mlflow.set_tracking_uri'), patch('mlflow.set_experiment'):
        system = MathTutoringSystem()
        yield system
        if mlflow.active_run():
            mlflow.end_run()