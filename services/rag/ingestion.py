from fastapi import UploadFile
import aiofiles
from aiofiles.os import makedirs
from config import Settings
from pypdf import PdfReader
from exceptions import FileTypeNotSupported
from providers.embedding import EmbeddingInterface
from repositories import DocumentRepository, ChunkRepository
from uuid import UUID, uuid4
from .chunking import ChunkingService
from pathlib import Path
from entities import User
from models.user import UserRole
from exceptions import UnauthorizedException

class IngestionService:
    def __init__(self, settings: Settings, embedding_model: EmbeddingInterface, 
                 doc_repo: DocumentRepository, chunk_repo: ChunkRepository,
                 chunking_service: ChunkingService):
        self.uploads_dir = settings.BASE_DIR / "assets"
        self.settings = settings
        self.embedding_model = embedding_model
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo
        self.chunking_service = chunking_service
         
    async def save_file(self, file: UploadFile) -> tuple[Path, str]:
        original_name = Path(file.filename or "upload.pdf").name
        new_name = f"{uuid4()}_{original_name}"
        file_path = self.uploads_dir / new_name
        await makedirs(self.uploads_dir, exist_ok=True)
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(self.settings.READ_FILE_CHUNK):
                await f.write(chunk)
        
        return file_path, original_name
    
    def parse_pdf(self, file_path: Path) -> str:
        content = ""
        try:
            pdf_reader = PdfReader(file_path, strict=True)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    content += f"{page_text}\n\n"
            return content
        except Exception:
            raise FileTypeNotSupported
        
    async def save_doc(self, file_name: str, user_id: UUID) -> UUID:
        new_doc = await self.doc_repo.create({
            "file_name": file_name,
            "created_by": user_id
        })
        
        return new_doc.id
     
        
    async def save_chunk(self, file_name: str, doc_id: UUID, content: str):
        chunks_content = self.chunking_service.split(content)
        chunks_index = list(range(len(chunks_content)))
        chunks_embeddings = await self.embedding_model.embed_index(
            title=file_name,
            content=chunks_content
        )
        
        no_chunks = await self.chunk_repo.create_many(
            doc_id,
            chunks_content,
            None,
            chunks_index,
            chunks_embeddings
        )
        
        return no_chunks
    
    async def ingest(self, file: UploadFile, user: User) -> int:
        if user.role != UserRole.ADMIN:
            raise UnauthorizedException
        
        file_path, title = await self.save_file(file)
        content = self.parse_pdf(file_path)
        if not content:
            raise ValueError("PDF has no content.")
        
        doc_id = await self.save_doc(title, user.id)
        chunks_no = await self.save_chunk(title, doc_id, content)
        return chunks_no