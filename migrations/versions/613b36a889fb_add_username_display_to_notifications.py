"""Add username display to notifications

Revision ID: 613b36a889fb
Revises: ec3dc0433e98
Create Date: 2024-11-12 19:22:00.131243

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '613b36a889fb'
down_revision = 'ec3dc0433e98'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sender_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            'fk_notification_sender_id',
            'user',
            ['sender_id'],
            ['id']
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('sender_id')

    # ### end Alembic commands ###