import pytest
from math_tutor.system_GB_Coach import LearningObjectives
import json
from pathlib import Path

def test_load_objectives(tmp_path):
    objectives_file = tmp_path / "objectifs.json"
    with open(objectives_file, 'w') as f:
        json.dump({"domaine_definition": {"description": "Test"}}, f)
    
    lo = LearningObjectives(objectives_file=objectives_file)
    assert "domaine_definition" in lo.objectives