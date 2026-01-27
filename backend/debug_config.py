import sys
import os
sys.path.append(os.getcwd())
try:
    from app.core.config import settings
    print("Settings loaded successfully")
    print(f"DB URL: {settings.DATABASE_URL.split('@')[-1]}") # Print non-sensitive part
except Exception as e:
    print(f"Error loading settings: {e}")
    import traceback
    traceback.print_exc()
