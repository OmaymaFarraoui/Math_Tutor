# import streamlit as st
# import os
# import pandas as pd

# # Accès au système parent
# if 'tutor' not in st.session_state or not hasattr(st.session_state, 'authenticated'):
#     st.error("Session non initialisée. Veuillez vous authentifier depuis la page d'accueil.")
#     st.page_link("app.py", label="← Page d'accueil")
#     st.stop()

# st.title("⚙️ Paramètres")


# def show_settings():
    
#     st.subheader("Configuration du Système")
#     if st.session_state.authenticated and st.session_state.tutor.current_student:
#         st.write(f"ID Étudiant: {st.session_state.tutor.current_student.student_id}")
#         st.write(f"Nom: {st.session_state.tutor.current_student.name or 'Non spécifié'}")
#         st.write(f"Dernière session: {st.session_state.tutor.current_student.last_session}")
    
#     st.subheader("Options")
#     if st.button("Exporter les données de progression"):
#         export_student_data()
    
#     st.subheader("Aide")
#     st.write("""
#     - **Authentification:** Créez ou chargez un profil étudiant
#     - **Session d'Apprentissage:** Pratiquez des exercices adaptés à votre niveau
#     - **Progression:** Visualisez vos statistiques et améliorations
#     """)

# def export_student_data():
#     if not st.session_state.authenticated or not st.session_state.tutor.current_student:
#         st.warning("Aucun étudiant connecté")
#         return
    
#     # Créer un DataFrame avec les données de l'étudiant
#     student_data = st.session_state.tutor.current_student.model_dump()
#     df = pd.DataFrame({
#         'ID': [student_data['student_id']],
#         'Nom': [student_data['name']],
#         'Niveau': [student_data['level']],
#         'Objectif Actuel': [student_data['current_objective']],
#         'Objectifs Complétés': [len(student_data['objectives_completed'])],
#         'Exercices Tentés': [len(student_data['learning_history'])]
#     })
    
#     # Convertir en CSV
#     csv = df.to_csv(index=False).encode('utf-8')
    
#     # Téléchargement
#     st.download_button(
#         label="Télécharger les données au format CSV",
#         data=csv,
#         file_name=f"progression_{student_data['student_id']}.csv",
#         mime="text/csv"
#     )

# show_settings()

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import json
import os

# Vérification de session
if 'tutor' not in st.session_state or not st.session_state.get('authenticated', False):
    st.error("Session non initialisée. Veuillez vous authentifier depuis la page d'accueil.")
    st.page_link("app.py", label="← Page d'accueil")
    st.stop()

# Configuration de la page
st.set_page_config(page_title="Paramètres", page_icon="⚙️")
st.title("⚙️ Paramètres du Compte")

def show_settings():
    student = st.session_state.tutor.current_student
    tutor = st.session_state.tutor
    
    # Section Profil Étudiant
    with st.expander("📝 Profil Étudiant", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Identifiant", student.student_id)
            st.metric("Niveau Actuel", student.level)
        with col2:
            st.metric("Objectifs Complétés", len(student.objectives_completed))
            st.metric("Dernière Activité", student.last_session or "Jamais")
        
        # Édition du profil
        if st.button("✏️ Modifier le Profil"):
            st.session_state.editing_profile = True
            
        if st.session_state.get('editing_profile', False):
            with st.form("profile_form"):
                new_name = st.text_input("Nom", value=student.name or "")
                if st.form_submit_button("Enregistrer"):
                    student.name = new_name
                    tutor.student_manager.save_student(student)
                    st.session_state.editing_profile = False
                    st.rerun()

    # Section Export des Données
    with st.expander("💾 Export des Données"):
        export_format = st.radio("Format d'export", ["CSV", "JSON"], horizontal=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Exporter la Progression"):
                export_student_data(export_format.lower())
        with col2:
            if st.button("Exporter l'Historique Complet"):
                export_full_history(export_format.lower())

    
    # Section Système
    with st.expander("🛠️ Options Système"):
        if st.button("🔍 Vérifier l'Intégrité des Données"):
            check_data_integrity()
        
        if st.button("🔄 Réinitialiser la Session"):
            st.session_state.clear()
            st.rerun()

    # Section Aide
    with st.expander("❓ Aide & Support"):
        st.write("""
        ### Guide d'utilisation
        - **Profil Étudiant:** Visualisez et modifiez vos informations
        - **Export des Données:** Téléchargez vos données de progression
        - **Statistiques:** Analysez votre performance détaillée
        
        ### Support Technique
        Pour toute assistance, contactez nous à support@mathtutor.com
        """)

def export_student_data(format_type='csv'):
    student = st.session_state.tutor.current_student
    data = {
        'ID': [student.student_id],
        'Nom': [student.name],
        'Niveau': [student.level],
        'Objectif Actuel': [student.current_objective],
        'Objectifs Complétés': [len(student.objectives_completed)],
        'Exercices Tentés': [len(student.learning_history)]
    }
    
    if format_type == 'csv':
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Télécharger CSV",
            data=csv,
            file_name=f"progression_{student.student_id}.csv",
            mime="text/csv"
        )
    else:
        json_data = json.dumps(data, indent=4)
        st.download_button(
            label="Télécharger JSON",
            data=json_data,
            file_name=f"progression_{student.student_id}.json",
            mime="application/json"
        )

def export_full_history(format_type='csv'):
    history = st.session_state.tutor.current_student.learning_history
    if not history:
        st.warning("Aucun historique disponible")
        return
    
    if format_type == 'csv':
        df = pd.DataFrame(history)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Télécharger l'Historique (CSV)",
            data=csv,
            file_name=f"historique_{st.session_state.tutor.current_student.student_id}.csv",
            mime="text/csv"
        )
    else:
        st.download_button(
            label="Télécharger l'Historique (JSON)",
            data=json.dumps(history, indent=4),
            file_name=f"historique_{st.session_state.tutor.current_student.student_id}.json",
            mime="application/json"
        )

def check_data_integrity():
    student = st.session_state.tutor.current_student
    issues = []
    
    if not student.student_id:
        issues.append("Identifiant étudiant manquant")
    if not student.learning_history:
        issues.append("Historique d'apprentissage vide")
    if not student.current_objective:
        issues.append("Objectif actuel non défini")
    
    if issues:
        st.warning(f"Problèmes détectés ({len(issues)}):")
        for issue in issues:
            st.write(f"- {issue}")
    else:
        st.success("✓ Toutes les données sont valides")

# Initialisation des états
if 'editing_profile' not in st.session_state:
    st.session_state.editing_profile = False

show_settings()