import pytest
from pathlib import Path
from math_tutor.utils.file_processor import FileProcessor

@pytest.fixture
def processor():
    return FileProcessor()

def test_text_extraction(processor):
    test_file = Path("test.txt")
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Test content")

        assert processor.extract_text_from_file(test_file) == "Test content"
    finally:
        if test_file.exists():
            test_file.unlink()

def test_pdf_processing(processor):
    # Nécessite un fichier PDF de test dans le dossier tests/data
    test_pdf = Path("tests/data/sample.pdf")
    if test_pdf.exists():
        text = processor.extract_text_from_file(test_pdf)
        assert "sample" in text.lower()