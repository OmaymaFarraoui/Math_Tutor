from unittest.mock import patch, Mock
from math_tutor.system_GB_Coach import MathTutoringSystem

def test_ui_prompts():
    with patch('rich.prompt.Prompt.ask', side_effect=["1", "Test", "42", "non"]):
        system = MathTutoringSystem()
        system.start_learning_session()  # Doit s'exécuter sans erreur