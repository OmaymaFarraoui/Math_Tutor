
## Fichier supplémentaire : deploy_models.py

import mlflow
from your_module import MathTutoringSystem

def deploy_model():
    """Enregistre le modèle dans le registry MLflow"""
    system = MathTutoringSystem()
    
    # Exemple: Enregistrer un modèle (adaptez à votre cas)
    with mlflow.start_run():
        mlflow.log_params({
            "model_type": "LLM",
            "llm_version": "llama-3.3-70b"
        })
        
        # Ici vous pourriez enregistrer votre modèle
        # mlflow.<framework>.log_model(...)
        
        print("Modèle déployé avec succès")

if __name__ == "__main__":
    deploy_model()