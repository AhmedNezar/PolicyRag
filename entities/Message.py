from .base import Base
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import UTC, datetime
import uuid
from models.messages import MessageStatus


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    prompt_content: Mapped[str] = mapped_column()
    response_content: Mapped[str] = mapped_column()
    status: Mapped[MessageStatus] = mapped_column(SQLEnum(MessageStatus), default=MessageStatus.PENDING)
    ttft: Mapped[float | None] = mapped_column()
    total_time: Mapped[float | None] = mapped_column()
    is_success: Mapped[bool | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )

    conversation = relationship("Conversation", back_populates="messages")
