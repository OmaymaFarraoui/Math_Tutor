import os
import json
import re
from tkinter import Tk, filedialog
from datetime import datetime # type: ignore
from pathlib import Path # type: ignore
from typing import Optional, Dict, List, Union
import chromadb
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
import pandas as pd
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import mlflow
from math_tutor.utils.file_processor import FileProcessor
from math_tutor.utils.long_term_memory import LongTermMemory

def setup_mlflow():
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
    mlflow.set_experiment("Math_Tutoring_System")

# Initialisation
load_dotenv()
console = Console()

class StudentProfile(BaseModel):
    student_id: str
    name: Optional[str] = None
    level: int = 1
    current_objective: Optional[str] = None
    learning_history: List[Dict] = Field(default_factory=list)
    objectives_completed: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_session: Optional[str] = None

class Exercise(BaseModel):
    exercise: str = Field(description="Une question unique et précise adaptée à l'objectif")
    solution: str = Field(description="Solution mathématique détaillée et rigoureuse")
    hints: List[str] = Field(
        description="Indice principal pour guider l'élève",
        default_factory=list
    )
    difficulty: str
    concept: str
class EvaluationResult(BaseModel):
    is_correct: bool = Field(..., description="Indique si la réponse est correcte")
    error_type: Optional[str] = Field(None, description="Type d'erreur identifié") 
    feedback: str = Field(..., description="Feedback pédagogique détaillé s l'erreur")
    detailed_explanation: str = Field(..., description="Explication mathématique complète")
    step_by_step_correction: str = Field(..., description="Correction étape par étape")
    recommendations: List[str] = Field(..., description="Recommandations personnalisées")

class CoachPersonal(BaseModel):
    motivation: str = Field(..., description="message motivant")
    strategy: str = Field(..., description="stratégie concrète") 
    tip: str = Field(..., description="astuce pratique")
    encouragement: List[str] = Field(..., description="phrase positive")

class LearningObjectives:
    def __init__(self, objectives_file="objectifs.json"):
        self.objectives_file = Path(objectives_file)
        self._load_objectives()

    def _load_objectives(self):
        try:
            with open(self.objectives_file, 'r', encoding='utf-8') as f:
                self.objectives = json.load(f)
                self.objectives_order = list(self.objectives.keys())
        except Exception as e:
            console.print(f"[red]Erreur de chargement des objectifs: {str(e)}[/red]")
            self.objectives = {}
            self.objectives_order = []

class StudentManager:
    def __init__(self, data_dir="students_data", enable_memory: bool = True):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.data_dir / "memory_db"))
        
        self.memory_enabled = enable_memory
        self.long_term_memory = self._safe_init_memory()

    def create_student(self, name=None):
        student_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:16]
        profile = StudentProfile(
            student_id=student_id,
            name=name,
            last_session=datetime.now().isoformat()
        )
        self.save_student(profile)
        return profile

    def load_student(self, student_id):
        student_file = self.data_dir / f"{student_id}.json"
        if not student_file.exists():
            return None
        try:
            with open(student_file, 'r', encoding='utf-8') as f:
                return StudentProfile(**json.load(f))
        except Exception as e:
            console.print(f"[red]Erreur de chargement: {str(e)}[/red]")
            return None

    def save_student(self, student):
        # Sauvegarde standard
        student_file = self.data_dir / f"{student.student_id}.json"
        try:
            with open(student_file, 'w', encoding='utf-8') as f:
                json.dump(student.model_dump(), f, indent=4)
            
            # Sauvegarde dans ChromaDB
            self._sync_to_long_term_memory(student)
        except Exception as e:
            console.print(f"[red]Erreur de sauvegarde: {str(e)}[/red]")
    def _safe_init_memory(self):
        """Initialisation avec fallback silencieux"""
        if not self.memory_enabled:
            return None
            
        try:
            from math_tutor.utils.long_term_memory import LongTermMemory
            memory = LongTermMemory("global_memory")
            memory.client.heartbeat()  # Test de connexion
            return memory
        except Exception as e:
            console.print(f"[yellow]⚠️ Mode dégradé: {str(e)}[/yellow]")
            return None


    def _sync_to_long_term_memory(self, student: StudentProfile) -> None:
        try:
            if not hasattr(self, 'long_term_memory') or not self.long_term_memory:
                console.print("[yellow]⚠️ Mémoire long terme non initialisée[/yellow]")
                return

            # 1. Synchronisation avec ID explicite
            self.long_term_memory.add_memory(
                content=f"Niveau atteint: {student.level}",
                metadata={
                    "type": "level_update",
                    "new_level": str(student.level),
                    "timestamp": datetime.now().isoformat()
                },
                id=f"level_{student.level}"  # Maintenant accepté
            )

        except Exception as e:
            console.print(f"[red]❌ Erreur synchronisation mémoire: {str(e)}[/red]")
            try:
                # Sauvegarde de secours corrigée
                backup_file = self.data_dir / f"{student.student_id}_backup.json"
                with open(backup_file, 'w') as f:
                    json.dump(student.model_dump(), f)
            except Exception as backup_error:
                console.print(f"[red]❌ Erreur sauvegarde secours: {str(backup_error)}[/red]")
class MathTutoringSystem:
    def __init__(self):
        self.llm = None
        try:
            self.llm = ChatGroq(
                api_key=os.getenv('GROQ_API_KEY'),
                model="groq/llama-3.3-70b-versatile",  
                temperature=0.7
            )
            self.setup_mlflow()
        except Exception as e:
            console.print(f"[yellow]Mode hors ligne activé: {str(e)}[/yellow]")
            self.llm = None 
        
        self.file_processor = FileProcessor()
        self.long_term_memory = None 

        # Initialiser les agents à None d'abord
        self.exercise_creator = None
        self.evaluator = None
        self.personal_coach = None
        
        self.student_manager = StudentManager()
        self.learning_objectives = LearningObjectives()
        self.current_student = None
        
        # Configurer les agents puis MLflow
        self._setup_agents()

    def _setup_agents(self):
        if self.llm:

            self.exercise_creator = Agent(
                role="Créateur d'exercices",
                name="ExerciseCreator",
                goal="Créer des exercices de mathématiques parfaitement adaptés au niveau de l'étudiant",
                backstory=""" Expert pédagogique spécialisé dans l'enseignement des mathématiques pour le baccalauréat marocain.
                             Maîtrise parfaitement la progression pédagogique et sait créer des exercices qui construisent 
                            graduellement la compréhension des concepts mathématiques.""",
                llm=self.llm,
                verbose=False
            )
            self.evaluator = Agent(
                role="Évaluateur Expert",
                name="AnswerEvaluator",
                goal="""Fournir des évaluations précises et pédagogiques des réponses mathématiques.
                Identifier clairement les erreurs et fournir des explications détaillées.""",
                backstory="""Professeur agrégé de mathématiques avec 15 ans d'expérience
                dans l'enseignement secondaire et supérieur. Spécialiste de la pédagogie différenciée.""",
                llm=self.llm,
                verbose=False,
                max_iter=15,  # Pour des analyses plus approfondies
                memory=True 
            )
            self.personal_coach = Agent(
            role="Coach Personnel en Mathématiques",
            name="PersonalMathCoach",
            goal="""Fournir un accompagnement personnalisé, des encouragements 
            et des stratégies d'apprentissage adaptées à chaque étudiant""",
            backstory="""Ancien professeur de mathématiques devenu coach scolaire,
            spécialisé dans la motivation et la résolution des blocages psychologiques
            liés à l'apprentissage des mathématiques. Utilise des techniques de
            pédagogie positive et de renforcement des compétences.""",
            llm=self.llm,
            verbose=False,
            memory=True,  
            max_iter=10   
        )
        if hasattr(self, 'mlflow_run'):
            try:
                mlflow.log_dict({
                    "exercise_creator": self.exercise_creator.model_dump(),
                    "evaluator": self.evaluator.model_dump(),
                    "personal_coach": self.personal_coach.model_dump()
                }, "agents_config.json")
            except Exception as e:
                console.print(f"[yellow]Erreur lors du logging des agents: {str(e)}[/yellow]")

    def load_model_from_registry(model_name: str, stage: str = "Production"):
        return mlflow.pyfunc.load_model(f"models:/{model_name}/{stage}")
    
    
    
    def authenticate_student(self):
        console.print(Panel.fit("🔐 Système de Tutorat Mathématique", style="bold blue"))
        
        choice = Prompt.ask(
            "1. Créer un profil\n2. Charger un profil",
            choices=["1", "2"],
            default="1"
        )
        
        success = False
        
        if choice == "1":
            name = Prompt.ask("Prénom (optionnel)")
            self.current_student = self.student_manager.create_student(name)
            console.print(f"[green]✅ Profil créé (ID: {self.current_student.student_id})[/green]")
            
            if self.learning_objectives.objectives_order:
                self.current_student.current_objective = self.learning_objectives.objectives_order[0]
                self.student_manager.save_student(self.current_student)
            success = True
        else:
            student_id = Prompt.ask("ID étudiant")
            self.current_student = self.student_manager.load_student(student_id)
            if not self.current_student:
                console.print("[red]❌ Profil non trouvé[/red]")
                success = False
            else:
                console.print(f"[green]✅ Bienvenue, {self.current_student.name or 'étudiant'}![/green]")
                success = True
        
        # Initialiser la mémoire long terme si authentification réussie
        if success and self.current_student:
            try:
                self.long_term_memory = LongTermMemory(self.current_student.student_id)
                self._load_initial_memories()
            except Exception as e:
                console.print(f"[yellow]⚠️ Impossible d'initialiser la mémoire long terme: {str(e)}[/yellow]")
                # Continuer sans mémoire long terme
                self.long_term_memory = None
        
        return success
    

    def _load_initial_memories(self):
        """Charge les mémoires initiales depuis le profil étudiant"""
        if not self.current_student:
            return
            
        # Ajouter les objectifs complétés comme mémoires
        for obj in self.current_student.objectives_completed:
            self.long_term_memory.add_memory(
                content=f"Objectif complété: {obj}",
                metadata={"type": "achievement", "objective": obj}
            )
        
        # Ajouter l'historique d'apprentissage
        for item in self.current_student.learning_history:
            self.long_term_memory.add_memory(
                content=f"Exercice: {item['exercise']} - Réponse: {item['answer']}",
                metadata={
                    "type": "exercise",
                    "correct": str(item['evaluation']),
                    "timestamp": item['timestamp']
                }
            )
    
    def setup_mlflow(self):
        """Configure le suivi MLflow avec gestion des erreurs"""
        try:
            mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
            mlflow.set_experiment("Math_Tutoring_System")
            self.mlflow_run = mlflow.start_run()
            
            # Enregistrez les paramètres du modèle
            mlflow.log_params({
                "llm_model": "llama-3.3-70b",
                "temperature": 0.7,
                "max_iter": 15
            })
        except Exception as e:
            console.print(f"[yellow]Avertissement MLflow: {str(e)}[/yellow]")
            self.mlflow_run = None

    def _generate_exercise(self) -> Optional[Exercise]:
        """Génère un exercice adapté à l'objectif actuel avec meilleure gestion des erreurs"""
        with mlflow.start_span("exercise_generation"):
            # Vérification de l'étudiant et de l'objectif
            if not self.current_student or not self.current_student.current_objective:
                console.print("[red]Aucun étudiant ou objectif défini[/red]")
                return None

            objective = self.learning_objectives.objectives.get(self.current_student.current_objective)
            if not objective:
                console.print(f"[red]Objectif non trouvé: {self.current_student.current_objective}[/red]")
                return None

            level_info = objective["niveaux"].get(str(self.current_student.level))
            if not level_info:
                console.print(f"[red]Niveau non trouvé: {self.current_student.level}[/red]")
                return None

            # Fallback de base
            default_exercise = Exercise(
                exercise=f"Résoudre: {level_info['example_functions'][0]}",
                solution=f"Solution: {level_info['objectives'][0]}",
                hints=["Appliquez les méthodes appropriées"],
                difficulty=level_info['name'],
                concept=self.current_student.current_objective
            )

            if not self.llm:
                return default_exercise

            try:
                # Prompt plus détaillé
                prompt = f"""
                Tu es un professeur de mathématiques expert. Crée un exercice avec:
                - Objectif: {objective['description']}
                - Niveau: {level_info['name']} 
                - Type: {self.current_student.current_objective}
                - Basé sur: {level_info['example_functions'][0]}

                L'exercice doit:
                1. Être clair et précis
                2. Avoir une solution détaillée
                3. Inclure 2-3 indices pédagogiques
                4. Correspondre au niveau de difficulté
                """

                task = Task(
                    description=prompt,
                    agent=self.exercise_creator,
                    expected_output="Un objet Exercise complet avec exercise, solution, hints, difficulty et concept",
                    output_pydantic=Exercise
                )

                crew = Crew(
                    agents=[self.exercise_creator],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=True 
                )

                result = crew.kickoff()
                print("\nEXercice:", result['exercise'])
                print("\nconcept:", result['concept'] )
                print("\ndifficulty:", result['difficulty'])
                print("\nhints:", "\n".join(result['hints']) )
                
                # Debug
                #console.print(f"[yellow]Résultat brut: {result}[/yellow]")
                if hasattr(self, 'mlflow_run') and self.mlflow_run:
                    try:
                        # Récupérer le niveau actuel comme métrique numérique
                        mlflow.log_metrics({
                            "student_level": self.current_student.level,
                            "hints_count": len(result['hints'])
                        })
                        
                        # Enregistrer les détails de la difficulté comme paramètre
                        mlflow.log_params({
                            "difficulty_name": result['difficulty'],
                            "concept": result['concept']
                        })
                        
                        mlflow.log_dict(result.model_dump(), "exercise_details.json")
                    except Exception as e:
                        console.print(f"[yellow]Erreur MLflow: {str(e)}[/yellow]")


                return result

            except Exception as e:
                console.print(f"[red]Erreur génération exercice: {str(e)}[/red]")
                return default_exercise
            
    def _evaluate_response(self, exercise: Exercise, answer: Union[str, Path]) -> EvaluationResult:
        """Évaluation robuste avec gestion directe Pydantic"""
        with mlflow.start_span("answer_evaluation"):
            # Cas fichier (PDF/image)
            if isinstance(answer, (Path, str)) and Path(answer).exists():
                try:
                    extracted_text = self.file_processor.extract_text_from_file(str(answer))
                    if not extracted_text:
                        console.print("[yellow]Aucun texte extrait du fichier[/yellow]")
                        return self._create_fallback_evaluation(exercise)
                    
                    # Utilisation directe avec Pydantic
                    return self._evaluate_prompt(exercise, extracted_text)
                    
                except Exception as e:
                    console.print(f"[red]Erreur traitement fichier: {str(e)}[/red]")
                    return self._create_fallback_evaluation(exercise)
            
            # Cas texte
            return self._evaluate_prompt(exercise, str(answer))
        
    def _evaluate_prompt(self, exercise: Exercise, answer: str) -> EvaluationResult:
        """Évalue une réponse textuelle"""
        prompt = f"""
        CONTEXTE D'ÉVALUATION
        ---------------------
        Exercice proposé : {exercise['exercise']}
        Solution de référence : {exercise['solution']}
        Réponse de l'étudiant : {answer}

        CRITÈRES D'ANALYSE DÉTAILLÉS
        ---------------------------
        1. Analyse du raisonnement:
        - Identifier toutes les étapes du raisonnement de l'étudiant
        - Vérifier la cohérence logique entre les étapes
        - Examiner la présence des justifications nécessaires

        2. Classification des erreurs:
        Types d'erreurs à considérer:
        - Erreur conceptuelle (compréhension des notions)
        - Erreur de calcul (opérations mathématiques)
        - Erreur de notation (écriture mathématique)
        - Erreur de méthode (choix de l'approche)
        - Erreur de logique (raisonnement)

        3. Recommandations pédagogiques:
        - Proposer des exercices de remédiation ciblés
        - Suggérer des ressources spécifiques
        - Indiquer les points à revoir en priorité
        """

        task = Task(
            description=prompt,
            agent=self.evaluator,
            expected_output="Objet EvaluationResult complet: Évaluation complète avec validation, feedback et recommandations",
            output_pydantic=EvaluationResult
        )

        crew = Crew(
            agents=[self.evaluator], 
            tasks=[task], 
            process=Process.sequential,
            verbose=False
        )
        
        return crew.kickoff()

    
        
    def _create_fallback_evaluation(self, exercise: Exercise) -> EvaluationResult:
        """Crée une évaluation de secours"""
        return EvaluationResult(
            is_correct=False,
            error_type="system_error",
            feedback="Erreur lors de l'évaluation",
            detailed_explanation=f"Explication: {exercise['concept']}",
            step_by_step_correction=exercise['solution'],
            recommendations=[
                "Vérifiez votre réponse manuellement",
                "Consultez la solution fournie",
                "Contactez votre enseignant"
            ]
        )

    def _provide_personalized_coaching(self, evaluation: EvaluationResult, exercise: Exercise) -> CoachPersonal:
        """Fournit un coaching personnalisé avec sortie Pydantic directe"""
        # Fallback de base
        fallback_coaching = CoachPersonal(
            motivation="Continuez vos efforts!",
            strategy="Revoyez la solution fournie",
            tip="Relisez attentivement les étapes",
            encouragement=["Vous progressez à chaque essai!"]
        )

        if not self.llm or not self.current_student:
            return fallback_coaching

        try:
            # Configuration directe de la tâche
            task = Task(
                description=self._build_coaching_prompt(exercise, evaluation),
                agent=self.personal_coach,
                expected_output="Retourne directement un objet CoachPersonal valide",
                output_pydantic=CoachPersonal  
            )

            # Exécution simplifiée
            result = Crew(
                agents=[self.personal_coach],
                tasks=[task],
                process=Process.sequential
            ).kickoff()

            # Journalisation
            if hasattr(self, 'mlflow_run'):
                self._log_coaching_data(exercise, evaluation, result)
            
            return result

        except Exception as e:
            console.print(f"[red]Erreur coaching: {str(e)}[/red]")
            return fallback_coaching

    def _build_coaching_prompt(self, exercise: Exercise, evaluation: EvaluationResult) -> str:
        """Prompt optimisé pour une sortie Pydantic directe"""
        return f"""
        [INSTRUCTIONS STRICTES]
        - Analyser la performance de l'étudiant
        - Générer UNIQUEMENT un objet CoachPersonal valide
        - Ne rien ajouter d'autre (pas de texte, markdown, etc.)

        [CONTEXTE]
        Exercice: {exercise['exercise']}
        Réussite: {'Correct' if evaluation['is_correct'] else 'Incorrect'}
        Erreur: {evaluation['error_type'] or 'Aucune'}

        [FORMAT DE SORTIE]
        {CoachPersonal}
        """

    def _log_coaching_data(self, exercise: Exercise, evaluation: EvaluationResult, coaching: CoachPersonal):
        """Journalisation des données de coaching"""
        try:
            mlflow.log_metrics({
                "coaching_strategy_len": len(coaching['strategy']),
                "encouragement_count": len(coaching['encouragement'])
            })
            
            mlflow.log_dict({
                "exercise": exercise.model_dump(),
                "evaluation": evaluation.model_dump(),
                "coaching": coaching.model_dump()
            }, "coaching_session.json")
        except Exception as e:
            console.print(f"[yellow]⚠️ Erreur journalisation: {str(e)}[/yellow]")

    
            
    def _display_progress_report(self):
        """Affiche un rapport de progression détaillé"""
        if not self.current_student:
            return

        console.print(Panel.fit("📊 Rapport de Progression", style="bold blue"))
        
        # Objectif actuel
        objective = self.learning_objectives.objectives.get(self.current_student.current_objective or "", {})
        console.print(f"🎯 Objectif actuel: {objective.get('description', 'Aucun')}")
        console.print(f"📈 Niveau actuel: {self.current_student.level}")
        
        # Objectifs complétés
        if self.current_student.objectives_completed:
            console.print("\n✅ Objectifs complétés:")
            for obj in self.current_student.objectives_completed:
                console.print(f"- {obj}")
        else:
            console.print("\n📌 Aucun objectif complété pour le moment")

        # Statistiques
        total_attempts = len(self.current_student.learning_history)
        correct_answers = sum(1 for x in self.current_student.learning_history if x.get('is_correct', False))
        console.print(f"\n📝 Tentatives: {total_attempts} | ✅ Correctes: {correct_answers}")
        correct_answers = sum(1 for x in self.current_student.learning_history if x.get('is_correct', False))
        accuracy = correct_answers / len(self.current_student.learning_history) if self.current_student.learning_history else 0
        
        mlflow.log_metrics({
            "student_level": self.current_student.level,
            "completion_rate": len(self.current_student.objectives_completed),
            "accuracy_rate": accuracy
        })

    def _display_evaluation(self, evaluation: EvaluationResult, exercise: Exercise ):
        """Affichage complet et structuré de l'évaluation"""
        console.print("\n" + "="*60)
        console.print(Panel.fit("📋 RÉSULTAT DE L'ÉVALUATION", style="bold blue"))

        # Section Résultat Principal
        if evaluation['is_correct']:
            console.print(Panel.fit(
                "✅ [bold green]RÉPONSE CORRECTE[/bold green]",
                style="green"
            ))
        else:
            error_display = evaluation['error_type']
            console.print(Panel.fit(
                f"❌ [bold red]RÉPONSE INCORRECTE[/bold red] ([yellow]{error_display}[/yellow])",
                style="red"
            ))

        # Section Feedback
        if evaluation['feedback']:
            console.print(Panel.fit(
                f"[bold]📝 Feedback:[/bold]\n{evaluation['feedback']}",
                border_style="blue"
            ))

        # Section Explication
        if evaluation["detailed_explanation"]:
            console.print(Panel.fit(
                f"[bold]🔍 Explication Détaillée:[/bold]\n{evaluation['detailed_explanation']}",
                border_style="blue"
            ))

        # Section Correction
        if evaluation['step_by_step_correction']:
            console.print(Panel.fit(
                f"[bold]✏️ Correction Étape par Étape:[/bold]\n{evaluation['step_by_step_correction']}",
                border_style="green"
            ))

        # Section Recommandations
        if evaluation['recommendations']:
            recs = "\n".join(f"• {rec}" for rec in evaluation['recommendations'])
            console.print(Panel.fit(
                f"[bold]💡 Recommandations:[/bold]\n{recs}",
                border_style="yellow"
            ))
        coaching = self._provide_personalized_coaching(evaluation, exercise)
        #tips = "\n".join(f"• {tip}" for tip in coaching['tip'])
        console.print(Panel.fit(
            f"[bold]🧠 Coaching Personnalisé:[/bold]\n"
            f"💪 [bold]Motivation:[/bold] {coaching['motivation']}\n"
            f"📚 [bold]Stratégie:[/bold] {coaching['strategy']}\n"
            f"💡 [bold]Astuce:[/bold]{coaching['tip']}\n"
            f"✨ [bold]Encouragement:[/bold] {coaching['encouragement']}",
            border_style="magenta"
        ))

        console.print("="*60 + "\n")

    


    def start_learning_session(self):
        if not self.authenticate_student():
            return

        console.print(Panel.fit(
            f"Bienvenue, {self.current_student.name or 'étudiant'}!",
            style="bold green"
        ))

        while True:  # Boucle principale de session
            # Afficher les infos du niveau
            objective = self.learning_objectives.objectives.get(self.current_student.current_objective or "")
            if not objective:
                console.print("[red]❌ Objectif non trouvé[/red]")
                break
                
            level_info = objective["niveaux"].get(str(self.current_student.level))
            if not level_info:
                console.print("[red]❌ Niveau non trouvé[/red]")
                break

            console.print(Panel.fit(
                f"🎯 {objective['description']}\n"
                f"📊 Niveau {self.current_student.level}: {level_info['name']}\n"
                f"📝 Objectifs: {' | '.join(level_info['objectives'])}",
                style="blue"
            ))

            # Générer le premier exercice
            exercise = self._generate_exercise()
            if not exercise:
                console.print("[red]❌ Impossible de générer un exercice[/red]")
                break

            while True:  # Boucle pour gérer un exercice (original ou similaire)
                
                attempts = 0
                max_attempts = 2
                last_evaluation = None
                exercise_completed = False

                while attempts < max_attempts:  # Boucle des tentatives
                    console.print(Panel.fit(
                        f"📝 Exercice (tentative {attempts + 1}/{max_attempts}):\n{exercise['exercise']}",
                        style="green"
                    ))
                    input_mode = Prompt.ask("✏️ Comment souhaitez-vous répondre ?", choices=["texte", "fichier", "hint", "quit"])

                    if input_mode.lower() == "quit":
                        return
                    elif input_mode.lower() == "hint":
                        hints = "\n".join(f"• {hint}" for hint in exercise['hints'])
                        console.print(f"\n💡[bold]Indice:[/bold]\n{hints}")
                        input_mode = Prompt.ask("✏️ Après l'indice, souhaitez-vous répondre par 'texte' ou 'fichier'?", choices=["texte", "fichier"])
                        attempts = max(0, attempts - 1) if attempts > 0 else 0

                    if input_mode == "texte":
                        answer = Prompt.ask("✏️ Entrez votre réponse")
                    elif input_mode == "fichier":
                        file_path = self.choisir_fichier()
                        if file_path and Path(file_path).exists():
                            answer = file_path
                        else:
                            console.print("[red]❌ Fichier non valide ou non sélectionné[/red]")
                            continue
        
                    else:
                        console.print("[red]❌ Mode de réponse inconnu[/red]")
                        continue


                    try:
                        evaluation = self._evaluate_response(exercise, answer)
                        self._display_evaluation(evaluation, exercise)
                        last_evaluation = evaluation
                        
                        self.current_student.learning_history.append({
                            "exercise": exercise['exercise'],
                            "answer": answer,
                            "evaluation": evaluation['is_correct'],
                            "timestamp": datetime.now().isoformat(),
                            "attempt": attempts + 1
                        })

                        if evaluation['is_correct']:
                            exercise_completed = True
                            break

                    except Exception as e:
                        console.print(f"[red]Erreur critique: {str(e)}[/red]")
                        evaluation = self._create_fallback_evaluation(exercise)
                        self._display_evaluation(evaluation,exercise)
                        last_evaluation = evaluation
                    
                    attempts += 1

                # Après les tentatives
                if exercise_completed:
                    # Mise à jour progression après exercice réussi
                    max_level = len(objective["niveaux"])
                    if self.current_student.level < max_level:
                        self.current_student.level += 1
                    else:
                        next_obj = self.learning_objectives.objectives_order.index(self.current_student.current_objective) + 1
                        if next_obj < len(self.learning_objectives.objectives_order):
                            self.current_student.objectives_completed.append(self.current_student.current_objective)
                            self.current_student.current_objective = self.learning_objectives.objectives_order[next_obj]
                            self.current_student.level = 1
                    
                    self.student_manager.save_student(self.current_student)
                    break  # Sort de la boucle d'exercice pour passer au suivant
                else:
                    choice = Prompt.ask(
                        "\nVoulez-vous un exercice similaire pour vous entraîner?",
                        choices=["oui", "non"],
                        default="oui"
                    )
                    if choice == "oui":
                        exercise = self._generate_similar_exercise(exercise)
                        continue  # Recommence avec nouvel exercice similaire
                    else:
                        break  # Sort de la boucle d'exercice

            # Demander si continuer avec nouvel objectif
            if not Prompt.ask("\nContinuer avec un nouvel exercice?", choices=["oui", "non"], default="oui"):
                break

        # Rapport final
        self._display_progress_report()
        console.print("\n[green]🎉 Session terminée![/green]")
    

    def choisir_fichier(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier"""
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(
                title="Choisissez un fichier",
                filetypes=[
                    ("Images", "*.png *.jpg *.jpeg"),
                    ("PDF", "*.pdf"),
                    ("Tous les fichiers", "*.*")
                ]
            )
            root.destroy()
            return file_path
        except Exception as e:
            console.print(f"[red]Erreur sélection fichier: {str(e)}[/red]")
            return None




    def _generate_similar_exercise(self, original_exercise: Exercise) -> Exercise:
        """Génère un exercice similaire au précédent (même concept et difficulté)"""
        if not self.llm:
            # Fallback simple - ajoute une variation à l'exercice original
            modified_exercise = original_exercise['exercise'].replace("=", "+ 1 =") if "=" in original_exercise['exercise'] else original_exercise['exercise'] + " (variation)"
            return Exercise(
                exercise=modified_exercise,
                solution=f"Solution similaire à: {original_exercise['solution']}",
                hints=original_exercise['hints'],
                difficulty=original_exercise['difficulty'],
                concept=original_exercise['concept']
            )

        try:
            task = Task(
                description=f"""
                Tu es un professeur de mathématiques expert.
                Génère un NOUVEL exercice SIMILAIRE mais DIFFÉRENT à l'exercice suivant, 
                avec la MÊME difficulté et portant sur le MÊME concept mathématique.

                CONTEXTE:
                - Exercice original: {original_exercise['exercise']}
                - Concept: {original_exercise['concept']}
                - Difficulté: {original_exercise['difficulty']}
                - Solution originale: {original_exercise['solution']}

                EXIGENCES:
                1. L'exercice doit tester les mêmes compétences mais avec des valeurs/nombres différents
                2. Doit être du même niveau de difficulté
                3. Doit inclure une solution complète
                4. Doit fournir des indices pédagogiques
                5. Doit être clair et précis
                """,
                expected_output="Un objet Exercise complet avec les champs: exercise, solution, hints, difficulty, concept",
                agent=self.exercise_creator,
                output_pydantic=Exercise
            )

            crew = Crew(
                agents=[self.exercise_creator], 
                tasks=[task],
                process=Process.sequential,
                verbose=False 
            )
            
            result = crew.kickoff()
            print("\nEXercice:", result['exercise'])
            print("\nconcept:", result['concept'] )
            print("\ndifficulty:", result['difficulty'])
            print("\nhints:", "\n".join(result['hints']) )
            return result
            
        except Exception as e:
            console.print(f"[red]Erreur lors de la génération d'exercice similaire: {str(e)}[/red]")
            # Fallback en cas d'erreur
            return self._generate_exercise()
        
    def monitor_student_progress(self):
        """Surveille la progression des étudiants"""
        from evidently.report import Report
        from evidently.metrics import (
            ColumnDriftMetric,
            DatasetDriftMetric,
            DatasetMissingValuesMetric
        )
        
        if not self.current_student or not self.current_student.learning_history:
            return

        # Convertir l'historique en DataFrame
        df = pd.DataFrame(self.current_student.learning_history)
        
        # Configurer le rapport
        report = Report(metrics=[
            ColumnDriftMetric(column_name="is_correct"),
            DatasetDriftMetric(),
            DatasetMissingValuesMetric()
        ])
        
        # Générer le rapport
        report.run(
            reference_data=df.iloc[:len(df)//2],  # Première moitié comme référence
            current_data=df.iloc[len(df)//2:],    # Deuxième moitié comme données courantes
        )
        
        # Sauvegarder le rapport
        if hasattr(self, 'mlflow_run') and self.mlflow_run:
            mlflow.log_dict(report.json(), "monitoring_report.json")
        
if __name__ == "__main__":
    try:
        system = MathTutoringSystem()
        system.start_learning_session()
    except Exception as e:
        console.print(f"[red]❌ Erreur critique: {str(e)}[/red]")
    finally:
        console.print("[blue]Merci d'avoir utilisé notre système![/blue]")