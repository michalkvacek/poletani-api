"""on delete cascade u photo adjustment

Revision ID: d42172840f6c
Revises: 4996ad8bc231
Create Date: 2023-10-30 16:30:57.118694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd42172840f6c'
down_revision = '4996ad8bc231'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('photo_adjustment_ibfk_1', 'photo_adjustment', type_='foreignkey')
    op.create_foreign_key(None, 'photo_adjustment', 'photo', ['photo_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'photo_adjustment', type_='foreignkey')
    op.create_foreign_key('photo_adjustment_ibfk_1', 'photo_adjustment', 'photo', ['photo_id'], ['id'])
    # ### end Alembic commands ###
