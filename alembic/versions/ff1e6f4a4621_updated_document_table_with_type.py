"""updated document table with type

Revision ID: ff1e6f4a4621
Revises: b55cbb6f865e
Create Date: 2024-07-01 13:51:46.889546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff1e6f4a4621'
down_revision: Union[str, None] = 'b55cbb6f865e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the Enum type first
    documenttype = sa.Enum('RAW', 'SUMMARY', 'FINAL_SUMMARY', name='documenttype')
    documenttype.create(op.get_bind(), checkfirst=True)

    # Then add the column
    op.add_column('documents', sa.Column('document_type', documenttype, nullable=False))
    op.create_unique_constraint(None, 'documents', ['vector_db_id'])


def downgrade() -> None:
    op.drop_constraint(None, 'documents', type_='unique')
    op.drop_column('documents', 'document_type')

    # Drop the Enum type
    documenttype = sa.Enum(name='documenttype')
    documenttype.drop(op.get_bind(), checkfirst=True)