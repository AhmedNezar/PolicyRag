from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from models.llm_calls import LLMCallType


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    call_type: Mapped[LLMCallType] = mapped_column(Enum(
        LLMCallType, native_enum=False, create_constraint=True,
        values_callable=lambda enum: [item.value for item in enum], name="llm_call_type",
    ))
    purpose: Mapped[str] = mapped_column()
    provider: Mapped[str | None] = mapped_column()
    model: Mapped[str | None] = mapped_column()
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), index=True)
    prompt_tokens: Mapped[int | None] = mapped_column()
    response_tokens: Mapped[int | None] = mapped_column()
    total_tokens: Mapped[int | None] = mapped_column()
    input_cost: Mapped[Decimal | None] = mapped_column()
    output_cost: Mapped[Decimal | None] = mapped_column()
    total_cost: Mapped[Decimal | None] = mapped_column()
    is_success: Mapped[bool | None] = mapped_column()
    error_type: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC))
