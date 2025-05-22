# MLOps Documentation

## 1. Configuration initiale

### Démarrer MLflow localement
```bash
mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root ./mlruns \
    --host 0.0.0.0 --port 5000