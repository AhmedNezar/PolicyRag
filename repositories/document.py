from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from entities import Document
from uuid import UUID

class DocumentRepository:
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def list_all(self, skip: int, take: int) -> list[Document]:
        result = await self.session.execute(
            select(Document).offset(skip).limit(take)
        )
        return result.scalars().all()
        
    async def get(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalars().first()
        
    async def create(self, document_data: dict) -> Document:
        new_document = Document(**document_data)
        self.session.add(new_document)
        await self.session.commit()
        await self.session.refresh(new_document)
        return new_document
    
    async def update(self, document: Document, update_data: dict) -> Document:
        for key, value in update_data.items():
            setattr(document, key, value)
            
        await self.session.commit()
        await self.session.refresh(document)
        return document
    
    async def delete(self, document: Document) -> None:
        await self.session.delete(document)
        await self.session.commit()