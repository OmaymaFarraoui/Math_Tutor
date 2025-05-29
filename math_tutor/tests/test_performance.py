import pytest
from math_tutor.system_GB_Coach import MathTutoringSystem
import time

@pytest.mark.performance
def test_exercise_generation_performance():
    system = MathTutoringSystem()
    system.current_student = system.student_manager.create_student("PerfTest")
    
    start_time = time.time()
    for _ in range(10):  # Test avec 10 générations
        system._generate_exercise()
    elapsed = time.time() - start_time
    
    assert elapsed < 5.0  # Doit prendre moins de 5 secondes pour 10 exercices