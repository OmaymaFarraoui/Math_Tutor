# math_tutor/tests/test_mlops.py
import pytest
from math_tutor.system_GB_Coach import MathTutoringSystem

def test_sample():
    """Test que le système peut s'initialiser correctement."""
    system = MathTutoringSystem()
    assert system is not None
    assert system.student_manager is not None
    assert system.learning_objectives is not None