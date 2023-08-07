"""add gpx to flight

Revision ID: 1e04cd7838dd
Revises: 2a320e1e093d
Create Date: 2023-08-07 18:55:00.914684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e04cd7838dd'
down_revision = '2a320e1e093d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('flight', sa.Column('gpx_track_filename', sa.String(length=128), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('flight', 'gpx_track_filename')
    # ### end Alembic commands ###