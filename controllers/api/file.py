from fastapi import APIRouter, UploadFile
from infrastructure.dependencies import IngestionServiceDep
from .auth import AuthenticateUserDep

from pydantic import BaseModel

class RetrieveScheme(BaseModel):
    query: str


file_router = APIRouter(
    prefix="/file"
)

@file_router.post("/upload")
async def upload(file: UploadFile, user: AuthenticateUserDep, ingestion_service: IngestionServiceDep):
    chunks = await ingestion_service.ingest(file, user)
    return {"indexed_chunks": chunks}