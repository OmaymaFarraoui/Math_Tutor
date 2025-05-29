from setuptools import setup, find_packages

setup(
    name="math_tutor",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'crewai>=0.28.8',
        'langchain-groq>=0.1.3',
        'chromadb>=0.4.24'
    ],
)