# import streamlit as st
# import pandas as pd
# import plotly.express as px

# # Accès au système parent
# if 'tutor' not in st.session_state or not hasattr(st.session_state, 'authenticated'):
#     st.error("Session non initialisée. Veuillez vous authentifier depuis la page d'accueil.")
#     st.page_link("app.py", label="← Page d'accueil")
#     st.stop()

# st.title("📊 Votre Progression")



# def show_progress():
#     if not st.session_state.authenticated or not st.session_state.tutor.current_student:
#         st.warning("Veuillez vous authentifier d'abord")
#         return
    
#     st.title(f"📊 Progression - {st.session_state.tutor.current_student.name or 'Étudiant'}")
    
#     # Informations générales
#     col1, col2 = st.columns(2)
#     with col1:
#         st.metric("Niveau Actuel", st.session_state.tutor.current_student.level)
#     with col2:
#         completed = len(st.session_state.tutor.current_student.objectives_completed)
#         st.metric("Objectifs Complétés", completed)
    
#     # Objectif actuel
#     objective = st.session_state.tutor.learning_objectives.objectives.get(
#         st.session_state.tutor.current_student.current_objective or "", {})
#     if objective:
#         st.subheader("Objectif Actuel")
#         st.write(objective.get('description', 'Aucun'))
        
#         # Barre de progression pour les niveaux
#         if "niveaux" in objective:
#             current_level = st.session_state.tutor.current_student.level
#             max_level = len(objective["niveaux"])
#             st.progress(current_level / max_level)
#             st.caption(f"Niveau {current_level} sur {max_level}")
    
#     # Historique des exercices
#     st.subheader("Historique des Exercices")
#     if st.session_state.tutor.current_student.learning_history:
#         history_df = pd.DataFrame(st.session_state.tutor.current_student.learning_history)
        
#         # Calculer les statistiques
#         total_attempts = len(history_df)
#         correct_answers = sum(history_df['evaluation'])
#         accuracy = correct_answers / total_attempts if total_attempts > 0 else 0
        
#         col1, col2 = st.columns(2)
#         col1.metric("Tentatives Total", total_attempts)
#         col2.metric("Taux de Réussite", f"{accuracy:.1%}")
        
#         # Afficher un graphique de progression
#         history_df['date'] = pd.to_datetime(history_df['timestamp'])
#         history_df['cumulative_correct'] = history_df['evaluation'].cumsum()
#         history_df['cumulative_accuracy'] = history_df['cumulative_correct'] / (history_df.index + 1)
        
#         st.line_chart(history_df.set_index('date')['cumulative_accuracy'])
        
#         # Afficher le tableau détaillé
#         with st.expander("Voir l'historique complet"):
#             st.dataframe(history_df[['date', 'exercise', 'evaluation']])
#     else:
#         st.info("Aucun historique d'exercices pour le moment")

# show_progress()

import streamlit as st
import pandas as pd
import plotly.express as px

# Vérification initiale
if 'tutor' not in st.session_state or not hasattr(st.session_state, 'authenticated'):
    st.error("Session non initialisée. Veuillez vous authentifier depuis la page d'accueil.")
    st.page_link("app.py", label="← Page d'accueil")
    st.stop()

# Titre principal unique
st.title("📊 Votre Progression")

def show_progress():
    student = st.session_state.tutor.current_student
    if not student:
        st.error("Aucun étudiant chargé")
        return
    
    # Section informations étudiant
    st.header(f"Progression de {student.name or 'Étudiant'}")
    
    # Metrics en colonnes
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Niveau Actuel", student.level)
    with col2:
        completed = len(student.objectives_completed)
        total = len(st.session_state.tutor.learning_objectives.objectives_order)
        st.metric("Objectifs", f"{completed}/{total}")
    with col3:
        accuracy = calculate_accuracy(student)
        st.metric("Taux de Réussite", f"{accuracy:.1%}")

    # Objectif actuel avec progression
    current_obj = st.session_state.tutor.learning_objectives.objectives.get(
        student.current_objective or "")
    
    if current_obj:
        with st.expander("📌 Objectif Actuel", expanded=True):
            st.write(current_obj.get('description', 'Description non disponible'))
            
            if "niveaux" in current_obj:
                current_level = student.level
                max_level = len(current_obj["niveaux"])
                progress = current_level / max_level
                
                st.progress(progress)
                st.caption(f"Progression : Niveau {current_level} sur {max_level}")
                
                # Graphique Plotly pour une meilleure visualisation
                fig = px.bar(
                    x=[f"Niveau {i+1}" for i in range(max_level)],
                    y=[1]*max_level,
                    color_discrete_sequence=['lightgrey']*max_level
                )
                fig.update_traces(
                    marker_color=['green' if i < current_level else 'lightgrey' 
                                for i in range(max_level)]
                )
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Niveaux",
                    yaxis_visible=False
                )
                st.plotly_chart(fig, use_container_width=True)

    # Historique des exercices
    st.header("📈 Historique des Exercices")
    if student.learning_history:
        history_df = process_history_data(student)
        
        tab1, tab2 = st.tabs(["Graphique", "Voir l'historique complet"])
        
        with tab1:
            fig = px.line(
                history_df,
                x='date',
                y='cumulative_accuracy',
                title='Évolution de votre précision'
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            st.dataframe(
                history_df[['date', 'exercise', 'evaluation']],
                column_config={
                    "date": "Date",
                    "exercise": "Exercice",
                    "evaluation": st.column_config.CheckboxColumn("Réussi")
                },
                hide_index=True
            )
    else:
        st.info("Aucun historique d'exercices pour le moment")
    
    # Section Statistiques Avancées
    with st.expander("📊 Statistiques Avancées"):
        if student.learning_history:
            history_df = pd.DataFrame(student.learning_history)
            history_df['date'] = pd.to_datetime(history_df['timestamp'])
            
            st.write("**Répartition des Réponses:**")
            fig = px.pie(
                names=["Correctes", "Incorrectes"],
                values=[history_df['evaluation'].sum(), len(history_df) - history_df['evaluation'].sum()],
                color_discrete_sequence=['red', 'green']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée statistique disponible")


def calculate_accuracy(student):
    if not student.learning_history:
        return 0
    correct = sum(1 for item in student.learning_history if item.get('evaluation', False))
    return correct / len(student.learning_history)

def process_history_data(student):
    history_df = pd.DataFrame(student.learning_history)
    history_df['date'] = pd.to_datetime(history_df['timestamp'])
    history_df['cumulative_correct'] = history_df['evaluation'].cumsum()
    history_df['cumulative_accuracy'] = history_df['cumulative_correct'] / (history_df.index + 1)
    return history_df

# Appel principal
show_progress()