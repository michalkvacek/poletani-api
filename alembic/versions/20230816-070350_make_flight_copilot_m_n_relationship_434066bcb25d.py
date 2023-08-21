"""make flight-copilot M:N relationship

Revision ID: 434066bcb25d
Revises: 71d100e65f04
Create Date: 2023-08-16 07:03:50.599364

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '434066bcb25d'
down_revision = '71d100e65f04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('flight_has_copilot',
    sa.Column('flight_id', sa.Integer(), nullable=False),
    sa.Column('copilot_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['copilot_id'], ['copilot.id'], ),
    sa.ForeignKeyConstraint(['flight_id'], ['flight.id'], ),
    sa.PrimaryKeyConstraint('flight_id', 'copilot_id')
    )
    op.drop_constraint('flight_ibfk_2', 'flight', type_='foreignkey')
    op.drop_column('flight', 'copilot_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('flight', sa.Column('copilot_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.create_foreign_key('flight_ibfk_2', 'flight', 'copilot', ['copilot_id'], ['id'])
    op.drop_table('flight_has_copilot')
    # ### end Alembic commands ###
