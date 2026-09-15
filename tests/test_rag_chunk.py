import pytest
from services.rag.chunking import ChunkingService
from types import SimpleNamespace

def make_service(chunk_size: int = 20, chunk_overlap: int = 0):
    settings = SimpleNamespace(
        CHUNK_SIZE=chunk_size,
        CHUNK_OVERLAP=chunk_overlap
    )
    
    return ChunkingService(settings)

def test_split_returns_chunks():
    service = make_service()
    result = service.split("Hello\n\nThis is a test")

    assert result == ["Hello", "This is a test"]
    
def test_split_empty_text_returns_empty_list():
    service = make_service()
    result = service.split("")

    assert result == []
    
def test_chunks_do_not_exceed_configured_size():
    service = make_service(chunk_size=5)

    result = service.split("abcdefghij")

    assert result
    assert all(len(chunk) <= 5 for chunk in result)