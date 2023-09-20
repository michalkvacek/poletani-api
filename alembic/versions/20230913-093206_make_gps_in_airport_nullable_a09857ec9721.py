"""make gps in airport nullable

Revision ID: a09857ec9721
Revises: 6e5cc5123a2b
Create Date: 2023-09-13 09:32:06.444179

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a09857ec9721'
down_revision = '6e5cc5123a2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('airport', 'gps_latitude',
               existing_type=mysql.FLOAT(),
               nullable=True)
    op.alter_column('airport', 'gps_longitude',
               existing_type=mysql.FLOAT(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('airport', 'gps_longitude',
               existing_type=mysql.FLOAT(),
               nullable=False)
    op.alter_column('airport', 'gps_latitude',
               existing_type=mysql.FLOAT(),
               nullable=False)
    # ### end Alembic commands ###