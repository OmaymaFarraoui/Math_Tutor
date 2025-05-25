import mlflow
from math_tutor.system_GB_Coach import MathTutoringSystem
from rich.console import Console
import warnings # type: ignore

# Suppress Pydantic warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

console = Console()

def deploy_model():
    """Déploie le modèle et enregistre les configurations dans MLflow"""
    try:
        # 1. Nettoyer les runs existants
        while mlflow.active_run():
            mlflow.end_run()
        
        console.print("\n[bold]🚀 Démarrage du déploiement[/bold]")
        
        # 2. Configurer MLflow
        mlflow.set_experiment("Math_Tutor_Deployment")
        
        with mlflow.start_run(run_name="Production_Deployment") as run:
            console.print(f"✅ Run MLflow démarré (ID: {run.info.run_id})")
            
            # 3. Initialiser le système minimal
            system = MathTutoringSystem()
            system.llm = None  # Désactiver l'LLM pour le déploiement
            
            # 4. Enregistrer les configurations
            mlflow.log_params({
                "system_version": "1.0",
                "llm_model": "llama-3.3-70b",
                "deployment_target": "production"
            })
            
            # 5. Enregistrer les objectifs pédagogiques
            if hasattr(system, 'learning_objectives'):
                objectives = system.learning_objectives.objectives
                mlflow.log_dict(objectives, "learning_objectives.json")
                console.print(f"📚 Objectifs pédagogiques enregistrés ({len(objectives)} concepts)")
            
            # 6. Marquer comme production
            mlflow.set_tag("env", "production")
            
            console.print("[bold green]✅ Déploiement réussi![/bold green]")
            console.print(f"🔗 Accédez au run: http://localhost:5000/#/experiments/{run.info.experiment_id}/runs/{run.info.run_id}")
            
            return True
            
    except Exception as e:
        console.print(f"[bold red]❌ Échec du déploiement:[/bold red] {str(e)}")
        return False

if __name__ == "__main__":
    deploy_model()