"""initial

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pastes table
    op.create_table(
        'pastes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('paste_id', sa.String(length=32), nullable=False),
        sa.Column('filename', sa.String(length=512), nullable=True),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('image_width', sa.Integer(), nullable=True),
        sa.Column('image_height', sa.Integer(), nullable=True),
        sa.Column('delete_token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('delete_token'),
        sa.UniqueConstraint('paste_id')
    )
    op.create_index(op.f('ix_pastes_paste_id'), 'pastes', ['paste_id'], unique=True)
    op.create_index(op.f('ix_pastes_delete_token'), 'pastes', ['delete_token'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pastes_delete_token'), table_name='pastes')
    op.drop_index(op.f('ix_pastes_paste_id'), table_name='pastes')
    op.drop_table('pastes')
