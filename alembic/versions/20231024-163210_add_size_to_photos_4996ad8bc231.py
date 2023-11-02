"""add size to photos

Revision ID: 4996ad8bc231
Revises: c3aef4ae2669
Create Date: 2023-10-24 16:32:10.826763

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4996ad8bc231'
down_revision = 'c3aef4ae2669'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('photo', sa.Column('width', sa.Integer(), nullable=False))
    op.add_column('photo', sa.Column('height', sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('photo', 'height')
    op.drop_column('photo', 'width')
    # ### end Alembic commands ###