"""gps u letiste nejsou nullable, pridani sloupce photo.exposed_at

Revision ID: 708fc32f6a3b
Revises: 804e55bbf855
Create Date: 2023-07-31 04:51:26.257834

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '708fc32f6a3b'
down_revision = '804e55bbf855'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('airport', 'gps_latitude',
               existing_type=mysql.FLOAT(),
               nullable=False)
    op.alter_column('airport', 'gps_longitude',
               existing_type=mysql.FLOAT(),
               nullable=False)
    op.add_column('photo', sa.Column('exposed_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('photo', 'exposed_at')
    op.alter_column('airport', 'gps_longitude',
               existing_type=mysql.FLOAT(),
               nullable=True)
    op.alter_column('airport', 'gps_latitude',
               existing_type=mysql.FLOAT(),
               nullable=True)
    # ### end Alembic commands ###