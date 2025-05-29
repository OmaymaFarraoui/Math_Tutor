# utils/file_processor.py
import os
import tempfile
from typing import Optional
from pathlib import Path
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF

class FileProcessor:
    def __init__(self):
        self.setup_tesseract()
    
    def setup_tesseract(self):
        """Configure le chemin d'accès à Tesseract OCR"""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.getenv("TESSERACT_PATH", "")
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                pytesseract.pytesseract.tesseract_cmd = path
                return
                
        raise EnvironmentError(
            "Tesseract OCR non trouvé. Veuillez l'installer et configurer le chemin."
        )
    
    def extract_text_from_file(self, file_path: str) -> Optional[str]:
        """Extrait le texte de différents types de fichiers"""
        try:
            file_path_str = str(file_path)
            if file_path_str.lower().endswith(('.png', '.jpg', '.jpeg')):
                return self._extract_text_from_image(file_path_str)
            elif file_path_str.lower().endswith('.pdf'):
                return self._extract_text_from_pdf(file_path_str)
            elif file_path_str.lower().endswith('.txt'):
                return self._extract_text_from_txt(file_path_str)
            else:
                raise ValueError("Format de fichier non supporté")
        except Exception as e:
            print(f"Erreur d'extraction: {str(e)}")
            return None
        
    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extrait le texte des fichiers TXT"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """Utilise OCR pour extraire le texte des images"""
        try:
            if not hasattr(pytesseract.pytesseract, 'tesseract_cmd'):
                raise EnvironmentError("Tesseract non configuré")
                
            img = Image.open(image_path)
            return pytesseract.image_to_string(img)
        except Exception as e:
            print(f"Erreur OCR: {str(e)}")
            try:
                with open(image_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return "Texte non extrait"

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extrait le texte d'un PDF en utilisant deux méthodes:
        1. PyMuPDF pour un extraction rapide du texte brut
        2. OCR via pdf2image + Tesseract si la méthode 1 échoue
        """
        try:
            # Méthode 1: Extraction directe avec PyMuPDF
            text = self._extract_text_with_pymupdf(pdf_path)
            if text.strip():  # Vérifie si le texte n'est pas vide
                return text
                
            # Méthode 2: Si méthode 1 échoue, utiliser OCR
            return self._extract_text_with_ocr(pdf_path)
            
        except Exception as e:
            print(f"Erreur extraction PDF: {str(e)}")
            return "Texte non extrait"

    def _extract_text_with_pymupdf(self, pdf_path: str) -> str:
        """Extrait le texte avec PyMuPDF (méthode rapide)"""
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def _extract_text_with_ocr(self, pdf_path: str) -> str:
        """Extrait le texte avec OCR (méthode plus lente mais plus fiable pour les PDF scannés)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convertir le PDF en images
            images = convert_from_path(
                pdf_path,
                output_folder=temp_dir,
                fmt='jpeg',
                thread_count=4
            )
            
            # Extraire le texte de chaque image
            full_text = ""
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f"page_{i}.jpg")
                image.save(image_path, 'JPEG')
                full_text += pytesseract.image_to_string(Image.open(image_path)) + "\n"
                
            return full_text.strip()