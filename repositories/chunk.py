from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from entities import Chunk
from uuid import UUID

class ChunkRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def list_all(self, skip: int, take: int) -> list[Chunk]:
        result = await self.session.execute(
            select(Chunk).offset(skip).limit(take)
        )
        return result.scalars().all()
        
    async def get(self, chunk_id: UUID) -> Chunk | None:
        result = await self.session.execute(
            select(Chunk).where(Chunk.id == chunk_id)
        )
        return result.scalars().first()
        
    async def create(self, chunk_data: dict) -> Chunk:
        new_chunk = Chunk(**chunk_data)
        self.session.add(new_chunk)
        await self.session.commit()
        await self.session.refresh(new_chunk)
        return new_chunk
    
    async def create_many(self, document_id: UUID, content: list[str], metadata: list[dict] | None, chunk_index: list[int], embeddings: list[list[float]]) -> int:
        batch_size = 50
        total_size = len(content)
        if metadata is None:
            metadata = [None] * total_size
            
        if len(content) != len(metadata) or len(content) != len(chunk_index) or len(content) != len(embeddings):
            raise ValueError("Lengths not equal")
                    
        for i in range(0, total_size, batch_size):
            content_batch = content[i:i+batch_size]
            metadata_batch = metadata[i:i+batch_size]
            index_batch = chunk_index[i:i+batch_size]
            embedding_batch = embeddings[i:i+batch_size]
            
            chunks = [
                Chunk(
                    document_id=document_id,
                    content=text,
                    metadata_=chunk_metadata,
                    chunk_index=index,
                    embedding=vector,
                )
                for text, chunk_metadata, index, vector in zip(content_batch, metadata_batch, index_batch, embedding_batch, strict=True)
            ]
        
            self.session.add_all(chunks)
            
        await self.session.commit()    
        return len(content)
            
            
    
    async def update(self, chunk: Chunk, update_data: dict) -> Chunk:
        for key, value in update_data.items():
            setattr(chunk, key, value)
            
        await self.session.commit()
        await self.session.refresh(chunk)
        return chunk
    
    async def delete(self, chunk: Chunk) -> None:
        await self.session.delete(chunk)
        await self.session.commit()
        
    async def search(self, embeddings: list[float], limit: int = 5) -> list[Chunk]:
        result = await self.session.execute(
            select(Chunk)
            .order_by(Chunk.embedding.cosine_distance(embeddings))
            .limit(limit)
        )
        
        return result.scalars().all()