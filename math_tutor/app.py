# app.py
import logging
import sys
import streamlit as st
from math_tutor.system_GB_Coach import MathTutoringSystem, LearningObjectives
import os
from datetime import datetime
import pandas as pd
os.environ["STREAMLIT_SERVER_ENABLE_STATIC_FILE_WATCHER"] = "false"
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def initialize_session_state():
    """Initialisation robuste du système"""
    if 'tutor' not in st.session_state:
        st.session_state.tutor = MathTutoringSystem()
        st.session_state.authenticated = False
        st.session_state.current_student = None
        st.session_state.current_exercise = None
        st.session_state.max_attempts = 2  # Ajoutez cette ligne
        st.session_state.current_attempt = 0
        
        # Force le chargement des objectifs
        if not hasattr(st.session_state.tutor, 'learning_objectives'):
            st.session_state.tutor.learning_objectives = LearningObjectives()
            st.session_state.tutor.learning_objectives._load_objectives()
def main():
    st.set_page_config(
        page_title="Tutorat Mathématique",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialisation obligatoire
    initialize_session_state()
    
    # Vérification plus robuste
    if not st.session_state.get('authenticated', False):
        show_authentication()
    else:
        show_main_interface()

   
def show_authentication():
    st.title("🔐 Authentification")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Nouvel Étudiant")
            with st.form("new_student"):
                name = st.text_input("Prénom (optionnel)")
                if st.form_submit_button("Créer profil"):
                    try:
                        # Création du nouvel étudiant
                        new_student = st.session_state.tutor.student_manager.create_student(name)
                        st.session_state.tutor.current_student = new_student
                        st.session_state.authenticated = True
                        st.session_state.current_exercise = None
                        
                        # Attribution d'un objectif par défaut
                        if not new_student.current_objective and st.session_state.tutor.learning_objectives.objectives_order:
                            new_student.current_objective = st.session_state.tutor.learning_objectives.objectives_order[0]
                        
                        # Sauvegarde
                        st.session_state.tutor.student_manager.save_student(new_student)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la création: {str(e)}")
        
        with col2:
            st.subheader("Étudiant Existant")
            with st.form("existing_student"):
                student_id = st.text_input("ID Étudiant")
                if st.form_submit_button("Charger profil"):
                    try:
                        loaded_student = st.session_state.tutor.student_manager.load_student(student_id)
                        if loaded_student:
                            st.session_state.tutor.current_student = loaded_student
                            st.session_state.authenticated = True
                            
                            # Vérification de l'objectif pour les profils existants
                            if not loaded_student.current_objective and st.session_state.tutor.learning_objectives.objectives_order:
                                loaded_student.current_objective = st.session_state.tutor.learning_objectives.objectives_order[0]
                                st.session_state.tutor.student_manager.save_student(loaded_student)
                            
                            st.rerun()
                        else:
                            st.error("Profil non trouvé")
                    except Exception as e:
                        st.error(f"Erreur lors du chargement: {str(e)}")
def show_main_interface():
    """Interface principale après authentification"""
    student = st.session_state.tutor.current_student
    
    # Sidebar
    st.sidebar.title(f"👤 {student.name or 'Étudiant'}")
    st.sidebar.markdown(f"**Niveau:** {student.level}")
    
    # Navigation
    page = st.sidebar.radio("Menu", ["Accueil", "Session", "Progression", "Paramètres"])
    
    if page == "Accueil":
        show_home()
    elif page == "Session":
        st.switch_page("./pages/session.py")
    elif page == "Progression":
        st.switch_page("./pages/progression.py")
    elif page == "Paramètres":
        st.switch_page("./pages/parametres.py")

def show_home():
    st.title("🏠 Tableau de bord")
    
    # Récupérer les données du système
    objective_info = st.session_state.tutor.get_current_objective_info()
    progress_info = st.session_state.tutor.get_student_progress()
    
    if not objective_info or not progress_info:
        st.warning("Aucun objectif défini")
        return
    
    # Affichage des informations
    with st.container():
        st.subheader("Objectif actuel")
        cols = st.columns([3, 1])
        cols[0].markdown(f"**{objective_info['description']}**")
        cols[1].metric("Niveau", f"{objective_info['level_name']} ({progress_info['level']}/{objective_info['total_levels']}")
        
        st.progress(progress_info['level'] / objective_info['total_levels'])
        
        with st.expander("Détails des objectifs"):
            for obj in objective_info['objectives']:
                st.markdown(f"- {obj}")
    
    # Statistiques
    with st.container():
        st.subheader("Votre progression")
        
        if not progress_info['history'].empty:
            correct = progress_info['history']['evaluation'].sum()
            total = len(progress_info['history'])
            
            col1, col2 = st.columns(2)
            col1.metric("Exercices complétés", f"{correct}/{total}")
            col2.metric("Taux de réussite", f"{(correct/total)*100:.1f}%")
            
            # Graphique simple
            progress_info['history']['date'] = pd.to_datetime(progress_info['history']['timestamp'])
            st.line_chart(progress_info['history'].set_index('date')['evaluation'].cumsum())
        else:
            st.info("Aucun historique d'exercices")

if __name__ == "__main__":
    main()