import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def fix_schema():
    print("Starting schema fix...")
    async with async_session_maker() as session:
        try:
            # Add image_id column
            print("Adding image_id column to face_images table...")
            await session.execute(text("ALTER TABLE face_images ADD COLUMN IF NOT EXISTS image_id VARCHAR(100);"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS ix_face_images_image_id ON face_images (image_id);"))
            await session.commit()
            print("Successfully added image_id column.")
        except Exception as e:
            print(f"Error adding column: {e}")
            await session.rollback()

if __name__ == "__main__":
    import sys
    import os
    # Add backend directory to python path
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    
    asyncio.run(fix_schema())
