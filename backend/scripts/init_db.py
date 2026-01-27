"""
Database initialization script
- Create default admin user
- Create default system configs
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.system import SystemConfig
from app.models.person import PersonGroup


async def create_default_admin():
    """Create default admin user"""
    async with AsyncSessionLocal() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print("[INFO] Admin user already exists, skipping...")
            return
        
        # Create admin user
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print("[OK] Default admin user created: admin / admin123")


async def create_default_configs():
    """Create default system configurations"""
    async with AsyncSessionLocal() as session:
        default_configs = [
            ("face_similarity_threshold", "0.6", "number", "Face similarity threshold (0.0-1.0)"),
            ("alert_cooldown_seconds", "60", "number", "Alert cooldown time in seconds"),
            ("data_retention_days", "30", "number", "Data retention days"),
            ("capture_quality", "85", "number", "JPEG capture quality (0-100)"),
        ]
        
        for key, value, value_type, description in default_configs:
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                config = SystemConfig(
                    config_key=key,
                    config_value=value,
                    value_type=value_type,
                    description=description,
                )
                session.add(config)
        
        await session.commit()
        print("[OK] Default system configs created")


async def create_default_person_groups():
    """Create default person groups"""
    async with AsyncSessionLocal() as session:
        default_groups = [
            ("Employee", "Company employees", "#22c55e", True, 0, 1),
            ("Visitor", "Registered visitors", "#3b82f6", True, 1, 2),
            ("VIP", "VIP guests", "#eab308", True, 2, 3),
            ("Blacklist", "Blacklisted persons", "#ef4444", True, 3, 4),
        ]
        
        for name, desc, color, alert_enabled, alert_priority, sort_order in default_groups:
            result = await session.execute(
                select(PersonGroup).where(PersonGroup.name == name)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                group = PersonGroup(
                    name=name,
                    description=desc,
                    color=color,
                    alert_enabled=alert_enabled,
                    alert_priority=alert_priority,
                    sort_order=sort_order,
                )
                session.add(group)
        
        await session.commit()
        print("[OK] Default person groups created")


async def main():
    print("=" * 50)
    print("Initializing database...")
    print("=" * 50)
    
    await create_default_admin()
    await create_default_configs()
    await create_default_person_groups()
    
    print("=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
