import sys
import os
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

def inspect_db():
    print(f"Connecting to: {settings.DATABASE_URL.split('@')[-1]}")
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    
    print("\n--- Tables ---")
    tables = inspector.get_table_names()
    print(tables)
    
    if "alert_logs" in tables:
        print("\n--- Columns in alert_logs ---")
        columns = inspector.get_columns("alert_logs")
        for c in columns:
            print(f"- {c['name']}: {c['type']}")
    else:
        print("\n!!! alert_logs table NOT FOUND !!!")

    if "system_configs" in tables:
        print("\n--- system_configs exists ---")
    else:
        print("\n!!! system_configs table NOT FOUND !!!")

if __name__ == "__main__":
    try:
        inspect_db()
    except Exception as e:
        print(f"Error: {e}")
