# Processus de Test

## Structure des tests
```
tests/
├── test_components.py       # Tests unitaires de base
├── test_integration.py      # Tests de workflow complet
├── test_with_mocks.py       # Tests avec dépendances mockées
├── test_performance.py      # Tests de performance
└── test_student_manager.py  # Tests spécifiques
```

## Exécution des tests

```bash
# Tous les tests
poetry run pytest -v

# Uniquement les tests unitaires
poetry run pytest -m "not performance"

# Avec couverture de code
poetry run pytest --cov=math_tutor --cov-report=html
```

## Workflow CI/CD
Les tests sont automatiquement exécutés :
- À chaque push
- Sur les pull requests
- Avec envoi des résultats à Codecov

## Tests de performance
Exécuter séparément avec :
```bash
poetry run pytest -m performance
```