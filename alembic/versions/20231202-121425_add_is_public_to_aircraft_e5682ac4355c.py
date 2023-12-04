"""add is_public to aircraft

Revision ID: e5682ac4355c
Revises: 91a9608b509d
Create Date: 2023-12-02 12:14:25.055308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5682ac4355c'
down_revision = '91a9608b509d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('aircraft', sa.Column('is_public', sa.Boolean(), server_default='0', nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('aircraft', 'is_public')
    # ### end Alembic commands ###
