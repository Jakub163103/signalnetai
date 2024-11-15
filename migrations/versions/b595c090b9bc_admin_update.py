"""Admin update

Revision ID: b595c090b9bc
Revises: bd27c124a61d
Create Date: 2024-11-14 19:14:37.720427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b595c090b9bc'
down_revision = 'bd27c124a61d'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add the 'role' column as nullable with a default value of 'User'
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(
            sa.Column(
                'role',
                sa.String(length=50),
                nullable=True,  # Initially nullable
                server_default='User'  # Temporary default
            )
        )

    # Step 2: Populate existing rows with the default value 'User'
    op.execute("UPDATE user SET role = 'User' WHERE role IS NULL")

    # Step 3: Alter the 'role' column to be non-nullable and remove the server default
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column(
            'role',
            nullable=False,  # Enforce NOT NULL
            server_default=None  # Remove the default
        )


def downgrade():
    # Reverse the upgrade steps
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(
            sa.Column(
                'role',
                sa.String(length=50),
                nullable=True  # Make it nullable for downgrade
            )
        )
    # Optionally, you can set a default or handle existing data here
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('role')
