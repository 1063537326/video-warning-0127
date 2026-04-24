"""add unidentified alert type

Revision ID: add_unidentified_type
Revises: 
Create Date: 2026-04-24 10:35:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_unidentified_type'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    向 alerttype 枚举添加 'unidentified' 值。

    PostgreSQL 不支持直接在事务中使用 ALTER TYPE ... ADD VALUE，
    需要在 autocommit 模式下执行。
    """
    # PostgreSQL: 向枚举类型添加新值
    op.execute("ALTER TYPE alerttype ADD VALUE IF NOT EXISTS 'unidentified'")


def downgrade() -> None:
    """
    PostgreSQL 不支持从枚举中移除值，降级时不做操作。
    """
    pass
