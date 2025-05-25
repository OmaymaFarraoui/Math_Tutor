from unittest.mock import patch, Mock, MagicMock
from math_tutor.system_GB_Coach import MathTutoringSystem
from crewai import Agent, Task, Crew

def test_with_mocked_llm():
    """Test avec LLM mocké"""
    # Create system instance
    system = MathTutoringSystem()
    
    # Mock the LLM
    system.llm = Mock()
    
    # Mock student authentication
    with patch('math_tutor.system_GB_Coach.Prompt.ask', side_effect=["1", "Test Student"]):
        assert system.authenticate_student() is True
    
    # Setup mock exercise data
    mock_exercise = {
        "exercise": "Test exercise",
        "solution": "Test solution", 
        "hints": ["Hint 1", "Hint 2"],
        "difficulty": "Test",
        "concept": "Test concept"
    }
    
    # Mock the CrewAI components
    with patch('math_tutor.system_GB_Coach.Agent') as mock_agent:
        with patch('math_tutor.system_GB_Coach.Task') as mock_task:
            with patch('math_tutor.system_GB_Coach.Crew') as mock_crew:
                # Configure mock return values
                mock_agent_instance = MagicMock()
                mock_agent.return_value = mock_agent_instance
                
                mock_task_instance = MagicMock()
                mock_task.return_value = mock_task_instance
                
                mock_crew_instance = MagicMock()
                mock_crew_instance.kickoff.return_value = mock_exercise
                mock_crew.return_value = mock_crew_instance
                
                # Test exercise generation
                exercise = system._generate_exercise()
                
                # Verify the exercise was generated
                assert exercise is not None
                assert exercise['exercise'] == "Test exercise"
                assert len(exercise['hints']) == 2
                
                # Verify the crew was used
                assert mock_crew.called
                assert mock_crew_instance.kickoff.called