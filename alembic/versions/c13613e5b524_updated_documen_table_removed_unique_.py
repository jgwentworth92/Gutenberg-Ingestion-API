"""updated documen table , removed unique contstraint

Revision ID: c13613e5b524
Revises: dd902c74bada
Create Date: 2024-07-01 16:54:27.097355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c13613e5b524'
down_revision: Union[str, None] = 'dd902c74bada'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('documents', 'document_type',
               existing_type=postgresql.ENUM('RAW', 'SUMMARY', 'FINAL_SUMMARY', name='documenttype'),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('documents', 'document_type',
               existing_type=postgresql.ENUM('RAW', 'SUMMARY', 'FINAL_SUMMARY', name='documenttype'),
               nullable=False)
    # ### end Alembic commands ###
