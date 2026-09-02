from .base import Base
from uuid import UUID, uuid4
from datetime import datetime, UTC
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Document(Base):
    __tablename__ = "documents"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_name: Mapped[str] = mapped_column()
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC), 
        onupdate=datetime.now(UTC)
    )
    
    user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    