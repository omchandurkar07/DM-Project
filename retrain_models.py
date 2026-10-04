"""Retrain all stock prediction models with the current sklearn version."""
import sys
sys.path.insert(0, '.')
from models.prediction import PredictionModel

pm = PredictionModel()
print('Retraining all models...')
results = pm.train_all()
for sym, m in results.items():
    if 'error' in m:
        print(f'  {sym}: ERROR - {m["error"]}')
    else:
        print(f'  {sym}: RMSE={m["rmse"]:.2f}  Acc={m["accuracy"]*100:.1f}%')
print('Done. Models saved to models/saved/')
