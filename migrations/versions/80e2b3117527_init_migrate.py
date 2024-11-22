"""init migrate

Revision ID: 80e2b3117527
Revises: 
Create Date: 2024-11-18 15:30:07.965424

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '80e2b3117527'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('contact_message',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('subject', sa.String(length=100), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('model',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('cost_per_signal', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('setting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('subscription',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('stripe_price_id', sa.String(length=50), nullable=False),
    sa.Column('features', sa.Text(), nullable=False),
    sa.Column('signals_per_day', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('stripe_price_id')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('subscription_id', sa.Integer(), nullable=True),
    sa.Column('profile_picture', sa.String(length=150), nullable=True),
    sa.Column('last_signal_reset', sa.DateTime(), nullable=True),
    sa.Column('signals_used', sa.Integer(), nullable=True),
    sa.Column('country', sa.String(length=2), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=True),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('allow_marketing_emails', sa.Boolean(), nullable=True),
    sa.Column('share_data_with_partners', sa.Boolean(), nullable=True),
    sa.Column('allow_profile_visibility', sa.Boolean(), nullable=True),
    sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['subscription_id'], ['subscription.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('cancellation_feedback',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=50), nullable=False),
    sa.Column('additional_comments', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('cancellation_feedback')
    op.drop_table('user')
    op.drop_table('subscription')
    op.drop_table('setting')
    op.drop_table('model')
    op.drop_table('log')
    op.drop_table('contact_message')
    # ### end Alembic commands ###
