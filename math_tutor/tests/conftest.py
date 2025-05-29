# tests/conftest.py
import pytest
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test_key')
    monkeypatch.setenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')