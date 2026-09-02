from .base import Base
from sqlalchemy import ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from uuid import UUID, uuid4
from datetime import datetime, UTC

class Chunk(Base):
    __tablename__ = "chunks"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    chunk_index: Mapped[int] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC), 
        onupdate=datetime.now(UTC)
    )
    
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_chunk_index"),
    )