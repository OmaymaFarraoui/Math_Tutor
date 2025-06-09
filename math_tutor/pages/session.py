import os
import streamlit as st
from math_tutor.system_GB_Coach import MathTutoringSystem
import datetime
import sympy as sp
import matplotlib.pyplot as plt

# Vérification initiale
if 'tutor' not in st.session_state or not hasattr(st.session_state, 'authenticated'):
    st.error("Session non initialisée. Veuillez vous authentifier depuis la page d'accueil.")
    st.page_link("app.py", label="← Page d'accueil")
    st.stop()

# Titre principal
st.title("📚 Session d'Apprentissage")

# Vérification d'authentification
if not st.session_state.authenticated:
    st.warning("Veuillez vous authentifier d'abord")
    st.stop()

# Initialisation des variables de session
if 'current_exercise' not in st.session_state:
    st.session_state.current_exercise = None
    st.session_state.attempts = 0
    st.session_state.max_attempts = 2

def show_learning_session():
    # Vérifications renforcées
    if not st.session_state.get('authenticated', False):
        st.warning("Authentification requise")
        st.stop()
    
    if not hasattr(st.session_state.tutor, 'current_student') or not st.session_state.tutor.current_student:
        st.error("Profil étudiant non chargé")
        st.stop()
    
    student = st.session_state.tutor.current_student
    
    # Vérification des objectifs
    if not hasattr(st.session_state.tutor, 'learning_objectives'):
        st.error("Configuration des objectifs manquante")
        st.stop()
    
    # Interface
    st.title(f"👤 {student.name or 'Étudiant'}")
    st.subheader(f"Niveau: {student.level}")
    
    # Vérification objectif actuel
    if not student.current_objective:
        if st.session_state.tutor.learning_objectives.objectives_order:
            student.current_objective = st.session_state.tutor.learning_objectives.objectives_order[0]
            st.session_state.tutor.student_manager.save_student(student)
            st.rerun()
        return
    
    objective = st.session_state.tutor.learning_objectives.objectives.get(student.current_objective)
    if not objective:
        st.error("Objectif invalide")
        return
    
    # Génération exercice
    if 'current_exercise' not in st.session_state or st.session_state.current_exercise is None:
        try:
            st.session_state.current_exercise = st.session_state.tutor._generate_exercise()
            st.session_state.attempts = 0
        except Exception as e:
            st.error(f"Erreur génération exercice: {str(e)}")
            return
    
    # Afficher l'exercice
    display_exercise()
    
  

def display_exercise():
    """Affiche l'exercice courant"""
    exercise = st.session_state.current_exercise
    
    st.divider()
    st.subheader("Exercice en cours")
    st.markdown(f"**{exercise.exercise}**")
    
    # Onglets pour réponse et indices
    tab_response, tab_hints = st.tabs(["Répondre", "Indices"])
    
    with tab_response:
        handle_response(exercise)
    
    with tab_hints:
        display_hints(exercise)

def handle_response(exercise):
    """Gère la soumission des réponses"""
    response_type = st.radio("Format de réponse", ["Texte", "Fichier"], horizontal=True)
    user_answer = None
    
    if response_type == "Texte":
        user_answer = st.text_area("Votre réponse", key="text_input")
    else:
        uploaded_file = st.file_uploader("Déposez votre fichier", 
                                       type=["png", "jpg", "jpeg", "pdf"])
        if uploaded_file:
            file_path = os.path.join("temp_uploads", uploaded_file.name)
            os.makedirs("temp_uploads", exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            user_answer = file_path
    
    if st.button("Soumettre", key="submit_btn"):
        process_answer(exercise, user_answer)

def process_answer(exercise, answer):
    """Traite la réponse de l'étudiant"""
    if not answer:
        st.warning("Veuillez fournir une réponse")
        return
    
    st.session_state.attempts += 1
    
    try:
        # Évaluation de la réponse
        evaluation = st.session_state.tutor._evaluate_response(exercise, answer)
        
        
        # Mise à jour de l'historique
        st.session_state.tutor.current_student.learning_history.append({
            "exercise": exercise.exercise,
            "answer": str(answer),
            "evaluation": evaluation.is_correct,
            "timestamp": datetime.datetime.now().isoformat(),
            "attempt": st.session_state.attempts
        })
        
        # Affichage des résultats
        display_results(evaluation,exercise)
        
        # Gestion de la progression
        if evaluation.is_correct:
            handle_success()
        elif st.session_state.attempts >= st.session_state.max_attempts:
            handle_failure()
            
    except Exception as e:
        st.error(f"Erreur lors de l'évaluation: {str(e)}")

def display_results(evaluation,exercise):
    """Affiche les résultats de l'évaluation"""
    if evaluation.is_correct:
        st.balloons()
        st.success("✅ Réponse correcte!")
        if st.button("exercice suivant", key="move_btn"):
            handle_success()
            st.session_state["text_input"] = ""

    else:
        st.error(f"❌ Réponse incorrecte: {evaluation.error_type or 'inconnue'})")
    
    with st.expander("Détails de l'évaluation"):
        display_streamlit_evaluation(evaluation, exercise)
    #     st.markdown(f"**Feedback:** {evaluation.feedback}")
    #     st.markdown("**Explication:**")
    #     st.markdown(evaluation.detailed_explanation)
        
    #     st.markdown("**Correction:**")
    #     st.markdown(evaluation.step_by_step_correction)
        
    #     st.markdown("**Recommandations:**")
    #     for rec in evaluation.recommendations:
    #         st.markdown(f"- {rec}")
    # with st.expander("Motivation"):
    #     st.markdown(f"**motivation:** {coach.motivation}")
    #     st.markdown("**strategy:**")
    #     st.markdown(coach.strategy)
        
    #     st.markdown("**Astuce:**")
    #     st.markdown(coach.tip)
        
    #     st.markdown("**Recommandations:**")
    #     for rec in coach.recommendations:
    #         st.markdown(f"- {rec}")

def handle_success():
    """Gère une réponse correcte"""
    objective = st.session_state.tutor.learning_objectives.objectives.get(st.session_state.tutor.current_student.current_objective or "")
    
    if objective:
        max_level = len(objective["niveaux"])
        if st.session_state.tutor.current_student.level < max_level:
            st.session_state.tutor.current_student.level += 1
        else:
            move_to_next_objective()
    
    st.session_state.tutor.student_manager.save_student(st.session_state.tutor.current_student)
    st.session_state.current_exercise = None  # Prêt pour un nouvel exercice

def move_to_next_objective():
    """Passe à l'objectif suivant"""
    current_idx = st.session_state.tutor.learning_objectives.objectives_order.index(
        st.session_state.tutor.current_student.current_objective)
    
    if current_idx + 1 < len(st.session_state.tutor.learning_objectives.objectives_order):
        st.session_state.tutor.current_student.objectives_completed.append(
            st.session_state.tutor.current_student.current_objective)
        st.session_state.tutor.current_student.current_objective = \
            st.session_state.tutor.learning_objectives.objectives_order[current_idx + 1]
        st.session_state.tutor.current_student.level = 1
        st.success("Nouvel objectif débloqué!")

def handle_failure():
    """Gère l'échec après plusieurs tentatives"""
    st.warning(f"Maximum de tentatives ({st.session_state.max_attempts}) atteint")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Nouvel exercice similaire"):
            st.session_state.current_exercise = st.session_state.tutor._generate_similar_exercise(st.session_state.current_exercise)
            st.session_state.attempts = 0
            st.rerun()
    
    with col2:
        if st.button("Nouvel exercice différent"):
            st.session_state.current_exercise = st.session_state.tutor._generate_exercise()
            st.session_state.attempts = 0
            st.rerun()

def display_hints(exercise):
    """Affiche les indices pour l'exercice"""
    if exercise.hints:
        st.write("Indices disponibles:")
        for i, hint in enumerate(exercise.hints, 1):
            with st.expander(f"Indice {i}"):
                st.write(hint)
    else:
        st.info("Aucun indice disponible pour cet exercice")

def display_streamlit_evaluation(evaluation, exercise):
    """Version adaptée pour Streamlit de l'affichage d'évaluation"""
    
    # Conteneur principal avec onglets
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Feedback", "🔍 Explication", "✏️ Correction", "🧠 Coaching"])
    
    with tab1:  # Onglet Feedback
        st.subheader("Feedback pédagogique")
        st.markdown(evaluation.feedback)
        
        if not evaluation.is_correct:
            st.warning(f"**Type d'erreur:** {evaluation.error_type}")
    
    with tab2:  # Onglet Explication
        st.subheader("Explication conceptuelle")
        st.markdown(evaluation.detailed_explanation)
        
        # Ajout possible de visualisations
        if "dérivée" in exercise.concept.lower():
            try:
                display_derivative_visualization(exercise)
            except:
                pass
    
    with tab3:  # Onglet Correction
        st.subheader("Correction étape par étape")
        steps = evaluation.step_by_step_correction.split('\n')
        
        for i, step in enumerate(steps, 1):
            st.markdown(f"{i}. {step}")
        
        # Solution complète sans expander imbriqué
        st.markdown("**Solution complète:**")
        st.markdown(f"```\n{exercise.solution}\n```")
    
    with tab4:  # Onglet Coaching
        coaching = st.session_state.tutor._provide_personalized_coaching(evaluation, exercise)
        
        st.subheader("Accompagnement personnalisé")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("💪 **Motivation**")
            st.info(coaching.motivation)
            
            st.markdown("📚 **Stratégie**")
            st.info(coaching.strategy)
        
        with col2:
            st.markdown("💡 **Astuce pratique**")
            st.success(coaching.tip)
            
            st.markdown("✨ **Encouragements**")
            for msg in coaching.encouragement:
                st.write(f"- {msg}")
        
        # Bouton pour générer un nouvel exercice similaire
        if st.button("🔄 Exercice similaire pour pratiquer", key="similar_exercise_btn"):
            st.session_state.current_exercise = st.session_state.tutor._generate_similar_exercise(exercise)
            st.rerun()
    
    # Section Recommandations
    st.divider()
    st.subheader("📌 Recommandations pour progresser")
    
    cols = st.columns(3)
    for i, rec in enumerate(evaluation.recommendations):
        with cols[i % 3]:
            st.markdown(f"- {rec}")

            
def display_derivative_visualization(exercise):
        """Visualisation des dérivées (exemple)"""
        
        
        x = sp.symbols('x')
        try:
            # Tentative d'extraction de la fonction de l'exercice
            expr_str = exercise.exercise.split(":")[-1].split("=")[0].strip()
            expr = sp.sympify(expr_str)
            
            # Calcul de la dérivée
            deriv = sp.diff(expr, x)
            
            # Création du graphique
            fig, ax = plt.subplots()
            sp.plot(expr, (x, -5, 5), label=f"f(x) = {expr}", ax=ax, show=False)
            sp.plot(deriv, (x, -5, 5), label=f"f'(x) = {deriv}", ax=ax, show=False)
            ax.legend()
            ax.grid(True)
            
            st.pyplot(fig)
            st.caption(f"Visualisation de la fonction et de sa dérivée")
        except:
            st.warning("Impossible de générer la visualisation pour cet exercice")
                

    



# Point d'entrée principal
show_learning_session()