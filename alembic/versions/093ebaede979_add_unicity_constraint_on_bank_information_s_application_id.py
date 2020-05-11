"""add_unicity_constraint_on_bank_information_s_application_id

Revision ID: 093ebaede979
Revises: 04928427ce14
Create Date: 2020-05-11 15:08:32.330029

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '093ebaede979'
down_revision = '04928427ce14'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('idx_bank_information_applicationId'), 'bank_information', ['applicationId'], unique=True)


def downgrade():
    op.drop_index('idx_bank_information_applicationId', table_name='bank_information')