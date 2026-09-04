from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import Settings


class ChunkingService:
    def __init__(self, settings: Settings):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    def split(self, text: str) -> list[str]:
        return self.splitter.split_text(text)