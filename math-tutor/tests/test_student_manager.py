import pytest
from math_tutor.system_GB_Coach import StudentManager, StudentProfile
from pathlib import Path
import json

def test_create_and_load_student(tmp_path):
    manager = StudentManager(data_dir=tmp_path)
    student = manager.create_student("Jean Dupont")
    
    assert (tmp_path / f"{student.student_id}.json").exists()
    loaded = manager.load_student(student.student_id)
    assert loaded.name == "Jean Dupont"

def test_save_student(tmp_path):
    manager = StudentManager(data_dir=tmp_path)
    student = StudentProfile(student_id="test123", name="Test")
    manager.save_student(student)
    
    with open(tmp_path / "test123.json") as f:
        data = json.load(f)
    assert data["name"] == "Test"