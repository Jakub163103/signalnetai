from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = 'cf2429d28fd6'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure all existing password_hash fields are populated
    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id, password FROM user")).fetchall()

    for user in users:
        if user[1]:  # Correct index for 'password'
            hashed_password = generate_password_hash(user[1])  # 'password' is at index 1
            connection.execute(
                sa.text("UPDATE user SET password_hash = :hashed_password WHERE id = :user_id"),
                {"hashed_password": hashed_password, "user_id": user[0]}  # 'id' is at index 0
            )
        else:
            # Handle users without a password, e.g., assign a default hashed password or prompt for reset
            hashed_password = generate_password_hash("defaultpassword")
            connection.execute(
                sa.text("UPDATE user SET password_hash = :hashed_password WHERE id = :user_id"),
                {"hashed_password": hashed_password, "user_id": user[0]}
            )

    # Alter the password_hash column to be NOT NULL
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.VARCHAR(length=128),
            nullable=False
        )
        # Drop the old password column
        batch_op.drop_column('password')


def downgrade():
    # Re-add the password column as nullable
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column('password', sa.VARCHAR(length=150), nullable=True))
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.VARCHAR(length=128),
            nullable=True
        )

    # Optionally, populate the password column with a default value or leave it as NULL
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE user SET password = '' WHERE password IS NULL"))