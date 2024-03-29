"""Add photo adjustment

Revision ID: 2acb6fa61028
Revises: 956d295689bf
Create Date: 2023-10-15 22:33:04.911765

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2acb6fa61028'
down_revision = '956d295689bf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('photo_adjustment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('photo_id', sa.Integer(), nullable=False),
    sa.Column('rotate', sa.Float(), nullable=True),
    sa.Column('contrast', sa.Float(), nullable=True),
    sa.Column('brightness', sa.Float(), nullable=True),
    sa.Column('saturation', sa.Float(), nullable=True),
    sa.Column('sharpness', sa.Float(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['photo_id'], ['photo.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('photo_adjustment')
    # ### end Alembic commands ###
