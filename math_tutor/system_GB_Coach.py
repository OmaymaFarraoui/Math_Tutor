import os
import json
import re
from tkinter import Tk, filedialog
from datetime import datetime, time # type: ignore
from pathlib import Path # type: ignore
from typing import Optional, Dict, List, Union
import chromadb
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
import pandas as pd
from pydantic import BaseModel, Field
import mlflow
import streamlit as st
import sympy as sp
import matplotlib.pyplot as plt
from math_tutor.utils.file_processor import FileProcessor
from math_tutor.utils.long_term_memory import LongTermMemory

def setup_mlflow():
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
    mlflow.set_experiment("Math_Tutoring_System")

# Initialisation
load_dotenv()

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
            st.error(f"Erreur de chargement des objectifs: {str(e)}")
            self.objectives = {}
            self.objectives_order = []

class StudentManager:
    def __init__(self, data_dir="students_data", enable_memory: bool = True):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.data_dir / "memory_db"))

        self.long_term_memory = self._initialize_memory(enable_memory)


    
    def _initialize_memory(self, enable_memory):
        import shutil
        db_path = Path("students_data/memory_db")
        if db_path.exists():
            try:
                shutil.rmtree(db_path)
            except Exception as e:
                print(f"⚠️ Nettoyage base échoué: {str(e)}")
        if not enable_memory:
            return None
            
        try:
            # Réinitialise la base si corrompue
            if hasattr(self, 'client'):
                try:
                    self.client.reset()
                except:
                    pass
                    
            from math_tutor.utils.long_term_memory import LongTermMemory
            memory = LongTermMemory("global_memory", client=self.client)
            
            if not memory.test_connection():
                raise ConnectionError("Échec test connexion mémoire")
                
            return memory
        except Exception as e:
            print(f"⚠️ Initialisation mémoire échouée : {str(e)}")
            return None

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
            st.error(f"Erreur de chargement: {str(e)}")
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
            st.error(f"Erreur de sauvegarde: {str(e)}")
    # def _safe_init_memory(self):
    #     """Initialisation avec fallback silencieux"""
    #     if not self.memory_enabled:
    #         return None
            
    #     try:
    #         # from math_tutor.utils.long_term_memory import LongTermMemory
    #         memory = LongTermMemory("global_memory")
    #         memory.client.heartbeat()  # Test de connexion
    #         return memory
    #     except Exception as e:
    #         st.warning(f"⚠️ Mode dégradé: {str(e)}")
    #         return None


    def _sync_to_long_term_memory(self, student: StudentProfile) -> None:
        """Version ultra-robuste avec réessai automatique"""
        if not self.long_term_memory:
            if not hasattr(self, '_warned_memory'):
                print("ℹ️ Mémoire désactivée - mode dégradé activé")
                self._warned_memory = True
            return

        metadata = {
            "type": "level_update",
            "student_id": student.student_id,
            "new_level": str(student.level),
            "timestamp": datetime.now().isoformat()
        }

        for attempt in range(3):  # 3 tentatives
            try:
                self.long_term_memory.upsert_memory(
                    content=f"Niveau {student.level} atteint par {student.name or 'anonyme'}",
                    metadata=metadata,
                    id=f"student_{student.student_id}_level_{student.level}"
                )
                return  # Succès, on sort
            except Exception as e:
                if attempt == 2:  # Dernière tentative
                    self._handle_sync_error(e, student)
                else:
                    print(f"⚠️ Tentative {attempt + 1} échouée, nouvelle tentative...")
                    time.sleep(1)  # Pause avant réessai

    def _handle_sync_error(self, error: Exception, student: StudentProfile):
        """Gestion centralisée des erreurs avec journalisation"""
        error_msg = f"❌ Erreur synchronisation mémoire: {str(error)}"
        print(error_msg)  # Log dans la console
        if 'st' in globals():  # Si Streamlit est disponible
            st.error(error_msg)
        
        # Sauvegarde d'urgence avec journalisation
        backup_dir = self.data_dir / "backups"
        try:
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"{timestamp}_{student.student_id}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "student": student.model_dump(),
                    "error": str(error),
                    "timestamp": datetime.now().isoformat(),
                    "attempt": "memory_sync"
                }, f, indent=4)
                
            print(f"✅ Sauvegarde secours créée: {backup_file}")
        except Exception as backup_error:
            print(f"❌ Échec sauvegarde secours: {str(backup_error)}")
class MathTutoringSystem:
    def __init__(self):
        self.llm = None
        try:
            self.llm = ChatGroq(
                api_key=os.getenv('GROQ_API_KEY'),
                model="llama-3.3-70b-versatile",  
                temperature=0.7
            )
            self.setup_mlflow()
        except Exception as e:
            st.error(f"Mode hors ligne activé: {str(e)}")
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
                st.error(f"Erreur lors du logging des agents: {str(e)}")

    def load_model_from_registry(model_name: str, stage: str = "Production"):
        return mlflow.pyfunc.load_model(f"models:/{model_name}/{stage}")
    
    
    
    def authenticate_student(self):
        """Version adaptée pour Streamlit"""
        if not hasattr(st.session_state, 'authenticated'):
            st.session_state.authenticated = False

        if st.session_state.authenticated:
            return True

        with st.form("auth_form"):
            choice = st.radio("Options", ["Créer un profil", "Charger un profil"])
            name = st.text_input("Prénom (optionnel)")
            student_id = st.text_input("ID étudiant") if choice == "Charger un profil" else None
            
            if st.form_submit_button("Valider"):
                if choice == "Créer un profil":
                    self.current_student = self.student_manager.create_student(name)
                    st.success(f"Profil créé (ID: {self.current_student.student_id})")
                    st.session_state.authenticated = True
                else:
                    self.current_student = self.student_manager.load_student(student_id)
                    if self.current_student:
                        st.success(f"Bienvenue, {self.current_student.name or 'étudiant'}!")
                        st.session_state.authenticated = True
                    else:
                        st.error("Profil non trouvé")
        
        return st.session_state.authenticated
    
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
            st.error(f"Avertissement MLflow: {str(e)}")
            self.mlflow_run = None


    def get_current_objective_info(self):
        """Retourne les infos de l'objectif actuel pour Streamlit"""
        if not self.current_student:
            return None
        
        objective = self.learning_objectives.objectives.get(self.current_student.current_objective or "", {})
        if not objective:
            return None
        
        level_info = objective["niveaux"].get(str(self.current_student.level), {})
        return {
            "description": objective.get("description", ""),
            "level_name": level_info.get("name", ""),
            "total_levels": len(objective["niveaux"]),
            "objectives": level_info.get("objectives", [])
        }

    def get_student_progress(self):
        """Retourne les statistiques de progression pour Streamlit"""
        if not self.current_student:
            return None
        
        return {
            "level": self.current_student.level,
            "completed": len(self.current_student.objectives_completed),
            "history": pd.DataFrame(self.current_student.learning_history)
        }

    def _generate_exercise(self) -> Optional[Exercise]:
        """Génère un exercice adapté à l'objectif actuel avec meilleure gestion des erreurs"""
        with mlflow.start_span("exercise_generation"):
            # Vérification de l'étudiant et de l'objectif
            if not self.current_student or not self.current_student.current_objective:
                st.error("Aucun étudiant ou objectif défini")
                return None

            objective = self.learning_objectives.objectives.get(self.current_student.current_objective)
            if not objective:
                st.error(f"Objectif non trouvé: {self.current_student.current_objective}")
                return None

            level_info = objective["niveaux"].get(str(self.current_student.level))
            if not level_info:
                st.error(f"Niveau non trouvé: {self.current_student.level}")
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
                # st.code("\nEXercice:", result['exercise'])
                # st.code("\nconcept:", result['concept'] )
                # st.code("\ndifficulty:", result['difficulty'])
                # st.code("\nhints:", "\n".join(result['hints']) )
                
                # Debug
                #console.print(f"[yellow]Résultat brut: {result}[/yellow]")
                if hasattr(self, 'mlflow_run') and self.mlflow_run:
                    try:
                        # Récupérer le niveau actuel comme métrique numérique
                        mlflow.log_metrics({
                            "student_level": self.current_student.level,
                            "hints_count": len(result.hints)
                        })
                        
                        # Enregistrer les détails de la difficulté comme paramètre
                        mlflow.log_params({
                            "difficulty_name": result.difficulty,
                            "concept": result.concept
                        })
                        
                        mlflow.log_dict(result.model_dump(), "exercise_details.json")
                    except Exception as e:
                        st.error(f"Erreur MLflow: {str(e)}")


                return result

            except Exception as e:
                st.error(f"Erreur génération exercice: {str(e)}")
                return default_exercise
            
    def _evaluate_response(self, exercise: Exercise, answer: Union[str, Path]) -> EvaluationResult:
        """Évaluation robuste avec gestion directe Pydantic"""
        with mlflow.start_span("answer_evaluation"):
            # Cas fichier (PDF/image)
            if isinstance(answer, (Path, str)) and Path(answer).exists():
                try:
                    extracted_text = self.file_processor.extract_text_from_file(str(answer))
                    if not extracted_text:
                        st.error("Aucun texte extrait du fichier")
                        return self._create_fallback_evaluation(exercise)
                    
                    # Utilisation directe avec Pydantic
                    return self._evaluate_prompt(exercise, extracted_text)
                    
                except Exception as e:
                    st.error(f"Erreur traitement fichier: {str(e)}")
                    return self._create_fallback_evaluation(exercise)
            
            # Cas texte
            return self._evaluate_prompt(exercise, str(answer))
        
    def _evaluate_prompt(self, exercise: Exercise, answer: str) -> EvaluationResult:
        """Évalue une réponse textuelle"""
        prompt = f"""
        CONTEXTE D'ÉVALUATION
        ---------------------
        Exercice proposé : {exercise.exercise}
        Solution de référence : {exercise.solution}
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
            detailed_explanation=f"Explication: {exercise.concept}",
            step_by_step_correction=exercise.solution,
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
            st.error(f"Erreur coaching: {str(e)}")
            return fallback_coaching

    def _build_coaching_prompt(self, exercise: Exercise, evaluation: EvaluationResult) -> str:
        """Prompt optimisé pour une sortie Pydantic directe"""
        return f"""
        [INSTRUCTIONS STRICTES]
        - Analyser la performance de l'étudiant
        - Générer UNIQUEMENT un objet CoachPersonal valide
        - Ne rien ajouter d'autre (pas de texte, markdown, etc.)

        [CONTEXTE]
        Exercice: {exercise.exercise}
        Réussite: {'Correct' if evaluation.is_correct else 'Incorrect'}
        Erreur: {evaluation.error_type or 'Aucune'}

        [FORMAT DE SORTIE]
        {CoachPersonal}
        """

    def _log_coaching_data(self, exercise: Exercise, evaluation: EvaluationResult, coaching: CoachPersonal):
        """Journalisation des données de coaching"""
        try:
            mlflow.log_metrics({
                "coaching_strategy_len": len(coaching.strategy),
                "encouragement_count": len(coaching.encouragement)
            })
            
            mlflow.log_dict({
                "exercise": exercise.model_dump(),
                "evaluation": evaluation.model_dump(),
                "coaching": coaching.model_dump()
            }, "coaching_session.json")
        except Exception as e:
            st.warning("⚠️ Erreur journalisation: {str(e)}")

    
    def start_learning_session(self):
        if not self.authenticate_student():
            return

        if 'current_exercise' not in st.session_state:
            st.session_state.current_exercise = None
            st.session_state.attempts = 0

        # Afficher les infos étudiant
        st.header(f"Bienvenue, {self.current_student.name or 'Étudiant'}!")

        st.header(
            f"Bienvenue, {self.current_student.name or 'étudiant'}!",
            divider="bold green"
        )

        while True:  # Boucle principale de session
            # Afficher les infos du niveau
            objective = self.learning_objectives.objectives.get(self.current_student.current_objective or "")
            if not objective:
                st.error("❌ Objectif non trouvé")
                break
                
            level_info = objective["niveaux"].get(str(self.current_student.level))
            if not level_info:
                st.error("❌ Niveau non trouvé")
                break

            st.header(
                f"🎯 {objective['description']}\n"
                f"📊 Niveau {self.current_student.level}: {level_info['name']}\n"
                f"📝 Objectifs: {' | '.join(level_info['objectives'])}",
                divider="blue"
            )

            # Générer le premier exercice
            exercise = self._generate_exercise()
            if not exercise:
                st.error("❌ Impossible de générer un exercice")
                break

            while True:  # Boucle pour gérer un exercice (original ou similaire)
                
                attempts = 0
                max_attempts = 2
                last_evaluation = None
                exercise_completed = False

                while attempts < max_attempts:  # Boucle des tentatives
                    st.header(
                        f"📝 Exercice (tentative {attempts + 1}/{max_attempts}):\n{exercise.exercise}",
                        divider="green"
                    )
                    input_mode = st.text_input("✏️ Comment souhaitez-vous répondre ?", choices=["texte", "fichier", "hint", "quit"])

                    if input_mode.lower() == "quit":
                        return
                    elif input_mode.lower() == "hint":
                        hints = "\n".join(f"• {hint}" for hint in exercise.hints)
                        st.info(f"\n💡[bold]Indice:[/bold]\n{hints}")
                        input_mode = st.text_input("✏️ Après l'indice, souhaitez-vous répondre par 'texte' ou 'fichier'?", choices=["texte", "fichier"])
                        attempts = max(0, attempts - 1) if attempts > 0 else 0

                    if input_mode == "texte":
                        answer = st.text_input("✏️ Entrez votre réponse")
                    elif input_mode == "fichier":
                        file_path = self.choisir_fichier()
                        if file_path and Path(file_path).exists():
                            answer = file_path
                        else:
                            st.error("❌ Fichier non valide ou non sélectionné")
                            continue
        
                    else:
                        st.error("❌ Mode de réponse inconnu")
                        continue


                    try:
                        evaluation = self._evaluate_response(exercise, answer)
                        self._display_evaluation(evaluation, exercise)
                        last_evaluation = evaluation
                        
                        self.current_student.learning_history.append({
                            "exercise": exercise.exercise,
                            "answer": answer,
                            "evaluation": evaluation.is_correct,
                            "timestamp": datetime.now().isoformat(),
                            "attempt": attempts + 1
                        })

                        if evaluation.is_correct:
                            exercise_completed = True
                            break

                    except Exception as e:
                        st.error(f"Erreur critique: {str(e)}")
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
                    choice  = st.text_input(
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
            if not st.text_input("\nContinuer avec un nouvel exercice?", choices=["oui", "non"], default="oui"):
                break

        # Rapport final
        self._display_progress_report()
        st.success("\n🎉 Session terminée!")
    

    def choisir_fichier(self):
        """Version Streamlit"""
        uploaded_file = st.file_uploader("Téléverser un fichier", 
                                    type=["png", "jpg", "jpeg", "pdf"])
        if uploaded_file:
            # Sauvegarde temporaire du fichier
            file_path = os.path.join("temp_uploads", uploaded_file.name)
            os.makedirs("temp_uploads", exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return file_path
        return None




    def _generate_similar_exercise(self, original_exercise: Exercise) -> Exercise:
        """Génère un exercice similaire au précédent (même concept et difficulté)"""
        if not self.llm:
            # Fallback simple - ajoute une variation à l'exercice original
            modified_exercise = original_exercise.exercise.replace("=", "+ 1 =") if "=" in original_exercise.exercise else original_exercise.exercise + " (variation)"
            return Exercise(
                exercise=modified_exercise,
                solution=f"Solution similaire à: {original_exercise.solution}",
                hints=original_exercise.hints,
                difficulty=original_exercise.difficulty,
                concept=original_exercise.concept
            )

        try:
            task = Task(
                description=f"""
                Tu es un professeur de mathématiques expert.
                Génère un NOUVEL exercice SIMILAIRE mais DIFFÉRENT à l'exercice suivant, 
                avec la MÊME difficulté et portant sur le MÊME concept mathématique.

                CONTEXTE:
                - Exercice original: {original_exercise.exercise}
                - Concept: {original_exercise.concept}
                - Difficulté: {original_exercise.difficulty}
                - Solution originale: {original_exercise.solution}

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
            # print("\nEXercice:", result['exercise'])
            # print("\nconcept:", result['concept'] )
            # print("\ndifficulty:", result['difficulty'])
            # print("\nhints:", "\n".join(result['hints']) )
            return result
            
        except Exception as e:
            st.error(f"Erreur lors de la génération d'exercice similaire: {str(e)}")
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
    # try:
    #     system = MathTutoringSystem()
    #     system.start_learning_session()
    # except Exception as e:
    # finally:
    #     st.code("Merci d'avoir utilisé notre système!")
    try:
        mlflow.log_metric("test", 1)
    except Exception as e:
        chromadb.logger.error(f"Erreur MLflow: {str(e)}")
    