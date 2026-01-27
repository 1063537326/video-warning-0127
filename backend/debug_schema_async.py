import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def inspect_db():
    print(f"Connecting to: {settings.DATABASE_URL.split('@')[-1]}")
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("\n--- Tables ---")
        # Async inspection is harder, let's query information_schema directly
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result.fetchall()]
        print(tables)
        
        if "alert_logs" in tables:
            print("\n--- Columns in alert_logs ---")
            result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'alert_logs'"))
            for row in result.fetchall():
                print(f"- {row[0]}: {row[1]}")
        else:
            print("\n!!! alert_logs table NOT FOUND !!!")
            
        if "system_configs" in tables:
             print("\n--- system_configs exists ---")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect_db())
