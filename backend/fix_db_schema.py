import asyncio
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def fix_schema():
    print("Starting schema fix...")
    async with AsyncSessionLocal() as session:
        try:
            # Add image_id column
            print("Adding image_id column to face_images table...")
            # We use a TRY block in SQL because IF NOT EXISTS for ADD COLUMN is only supported in newer Postgres (v9.6+), assuming user has it.
            # But asyncpg/sqlalchemy might raise error if transaction block persists error.
            # Simple check:
            await session.execute(text("ALTER TABLE face_images ADD COLUMN IF NOT EXISTS image_id VARCHAR(100);"))
            await session.commit()
            
            print("Adding index...")
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_face_images_image_id ON face_images (image_id);"))
            await session.commit()
            print("Successfully added image_id column.")
        except Exception as e:
            print(f"Error adding column (might already exist or other error): {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(fix_schema())
