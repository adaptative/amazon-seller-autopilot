import sys
from pathlib import Path

# Add the api package root to Python path so `from main import app` resolves
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
