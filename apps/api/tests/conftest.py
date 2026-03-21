import sys
from pathlib import Path

# Add project root to Python path so `from apps.api.main import app` resolves
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
