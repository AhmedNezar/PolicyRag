from fastapi import APIRouter, UploadFile
from infrastructure.dependencies import IngestionServiceDep
from .auth import AuthenticateUserDep

from pydantic import BaseModel
from infrastructure.dependencies import GuardrailServiceDep

class RetrieveScheme(BaseModel):
    query: str


file_router = APIRouter(
    prefix="/file"
)

@file_router.post("/upload")
async def upload(file: UploadFile, user: AuthenticateUserDep, ingestion_service: IngestionServiceDep):
    chunks = await ingestion_service.ingest(file, user)
    return {"indexed_chunks": chunks}

@file_router.post("/retrieve")
async def retrieve(request: RetrieveScheme, guardrail: GuardrailServiceDep):
    prompt = await guardrail.route(request.query)
    return {"prompt": prompt}