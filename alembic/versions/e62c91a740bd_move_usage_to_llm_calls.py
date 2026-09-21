"""Move message usage to a per-call ledger, preserving historical values.

Downgrade restores answer usage only; other call records cannot fit the old schema.
"""
from alembic import op
import sqlalchemy as sa

revision = "e62c91a740bd"
down_revision = "0345f6366ac4"
branch_labels = None
depends_on = None

TOKEN_FIELDS = ("prompt_tokens", "response_tokens", "total_tokens")
COST_FIELDS = ("input_cost", "output_cost", "total_cost")


def upgrade():
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("call_type", sa.Enum("generation", "embedding", name="llm_call_type",
                                     native_enum=False, create_constraint=True), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("message_id", sa.Uuid(), sa.ForeignKey("messages.id", ondelete="SET NULL")),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        *(sa.Column(name, sa.Integer(), nullable=True) for name in TOKEN_FIELDS),
        *(sa.Column(name, sa.Numeric(), nullable=True) for name in COST_FIELDS),
        sa.Column("is_success", sa.Boolean(), nullable=True),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_calls_message_id", "llm_calls", ["message_id"])
    op.create_index("ix_llm_calls_conversation_id", "llm_calls", ["conversation_id"])
    fields = TOKEN_FIELDS + COST_FIELDS
    # Message UUIDs are safe IDs for the initial rows of this separate table.
    # Historical provider and auxiliary-call usage were not stored; leave them unknown.
    op.execute(sa.text("""
        INSERT INTO llm_calls
            (id, call_type, purpose, model, message_id, conversation_id,
             """ + ", ".join(fields) + """, is_success, created_at)
        SELECT m.id, 'generation', 'legacy_answer', c.model_type, m.id, m.conversation_id,
            """ + ", ".join("m." + name for name in fields) + """, m.is_success, m.created_at
        FROM messages m JOIN conversations c ON c.id = m.conversation_id
        WHERE """ + " OR ".join("m." + name + " IS NOT NULL" for name in fields)))
    for name in fields:
        op.drop_column("messages", name)


def downgrade():
    for name in TOKEN_FIELDS:
        op.add_column("messages", sa.Column(name, sa.Integer(), nullable=True))
    for name in COST_FIELDS:
        op.add_column("messages", sa.Column(name, sa.Numeric(), nullable=True))
    # SUM preserves unknown values when all answer-call values are NULL.
    for name in TOKEN_FIELDS + COST_FIELDS:
        op.execute(sa.text(f"""
            UPDATE messages SET {name} = (
                SELECT SUM({name}) FROM llm_calls
                WHERE llm_calls.message_id = messages.id
                AND call_type = 'generation' AND purpose IN ('answer', 'legacy_answer')
            )
        """))
    op.drop_index("ix_llm_calls_conversation_id", table_name="llm_calls")
    op.drop_index("ix_llm_calls_message_id", table_name="llm_calls")
    op.drop_table("llm_calls")
