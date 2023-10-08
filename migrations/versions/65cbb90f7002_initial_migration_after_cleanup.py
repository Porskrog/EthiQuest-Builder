"""Initial migration after cleanup

Revision ID: 65cbb90f7002
Revises: 
Create Date: 2023-10-08 19:47:20.510426

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65cbb90f7002'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Dilemmas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('question', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('Users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('UserID', sa.String(length=50), nullable=True),
    sa.Column('cookie_id', sa.String(length=100), nullable=True),
    sa.Column('LastVisit', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('UserID'),
    sa.UniqueConstraint('cookie_id')
    )
    op.create_table('Options',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(length=500), nullable=True),
    sa.Column('pros', sa.String(length=500), nullable=True),
    sa.Column('cons', sa.String(length=500), nullable=True),
    sa.Column('DilemmaID', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['DilemmaID'], ['Dilemmas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ViewedDilemmas',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('dilemma_id', sa.Integer(), nullable=True),
    sa.Column('Timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['dilemma_id'], ['Dilemmas.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['Users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('UserChoices',
    sa.Column('ChoiceID', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('UserID', sa.Integer(), nullable=True),
    sa.Column('DilemmaID', sa.Integer(), nullable=True),
    sa.Column('OptionID', sa.Integer(), nullable=True),
    sa.Column('Timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['DilemmaID'], ['Dilemmas.id'], ),
    sa.ForeignKeyConstraint(['OptionID'], ['Options.id'], ),
    sa.ForeignKeyConstraint(['UserID'], ['Users.id'], ),
    sa.PrimaryKeyConstraint('ChoiceID')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('UserChoices')
    op.drop_table('ViewedDilemmas')
    op.drop_table('Options')
    op.drop_table('Users')
    op.drop_table('Dilemmas')
    # ### end Alembic commands ###