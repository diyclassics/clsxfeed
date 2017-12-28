"""empty message

Revision ID: 25f7d130096d
Revises: 
Create Date: 2017-12-27 21:42:27.407830

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '25f7d130096d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('entries')
    # ### end Alembic commands ###
