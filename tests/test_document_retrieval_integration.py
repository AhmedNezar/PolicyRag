import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from config import get_settings
from entities import Chunk, Document, User
from infrastructure.database import Database
from infrastructure.prompts import BASE_PROMPT, CONTEXT_PROMPT, POLICY_QUESTION_PROMPT
from models import UserRole
from providers.llm.LLMFactory import LLMFactory
from repositories import ChunkRepository, DocumentRepository
from services.rag.ingestion import IngestionService
from services.rag.retrieval import RetrievalService


REMOTE_QUESTION = "How many days may employees work remotely?"
REMOTE_VARIANTS = [
    "HOW MANY DAYS MAY EMPLOYEES WORK REMOTELY?",
    "how many days may employees work remotely?",
    "How many days may employes work remotly?",
]
CAFETERIA_QUESTION = "What time does the cafeteria close?"


class FixedChunkingService:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks

    def split(self, content: str) -> list[str]:
        return self.chunks


class FixedEmbeddingModel:
    def __init__(
        self,
        document_embeddings: list[list[float]],
        query_embeddings: dict[str, list[float]],
    ):
        self.document_embeddings = document_embeddings
        self.query_embeddings = query_embeddings

    async def embed_index(
        self,
        title: str,
        content: list[str],
    ) -> list[list[float]]:
        assert len(content) == len(self.document_embeddings)
        return self.document_embeddings

    async def embed_retrieve(self, query: str) -> list[float]:
        return self.query_embeddings[query]


class AnswerEvaluation(BaseModel):
    correctness: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    readability: int = Field(ge=1, le=5)
    safe: bool
    reason: str


def unit_vector(size: int, position: int) -> list[float]:
    vector = [0.0] * size
    vector[position] = 1.0
    return vector


@pytest_asyncio.fixture
async def indexed_policy_system():
    settings = get_settings()
    database = Database(settings)
    user_id = None
    document_id = None

    remote_content = (
        "Employees may work remotely up to two days per week with manager approval."
    )
    cafeteria_content = "The company cafeteria closes at 4:00 PM on weekdays."
    remote_vector = unit_vector(settings.EMBEDDING_VECTOR_SIZE, 17)
    cafeteria_vector = unit_vector(settings.EMBEDDING_VECTOR_SIZE, 29)

    embedding_model = FixedEmbeddingModel(
        document_embeddings=[remote_vector, cafeteria_vector],
        query_embeddings={
            REMOTE_QUESTION: remote_vector,
            **{query: remote_vector for query in REMOTE_VARIANTS},
            CAFETERIA_QUESTION: cafeteria_vector,
        },
    )

    try:
        async with database.async_session() as session:
            user = User(
                username=f"retrieval_test_{uuid4().hex}",
                hashed_password="not-used",
                role=UserRole.ADMIN,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

            document_repo = DocumentRepository(session)
            chunk_repo = ChunkRepository(session)
            ingestion_service = IngestionService(
                settings=settings,
                embedding_model=embedding_model,
                doc_repo=document_repo,
                chunk_repo=chunk_repo,
                chunking_service=FixedChunkingService(
                    [remote_content, cafeteria_content]
                ),
            )
            retrieval_service = RetrievalService(chunk_repo=chunk_repo, model=None)

            file_name = f"policy-{uuid4().hex}.pdf"
            document_id = await ingestion_service.save_doc(file_name, user.id)
            indexed_count = await ingestion_service.save_chunk(
                file_name=file_name,
                doc_id=document_id,
                content="Fixed policy content",
            )

            saved_document = await document_repo.get(document_id)
            saved_chunks_result = await session.execute(
                select(Chunk)
                .where(Chunk.document_id == document_id)
                .order_by(Chunk.chunk_index)
            )

            yield SimpleNamespace(
                settings=settings,
                embedding_model=embedding_model,
                retrieval_service=retrieval_service,
                indexed_count=indexed_count,
                document=saved_document,
                chunks=saved_chunks_result.scalars().all(),
                file_name=file_name,
                remote_content=remote_content,
                cafeteria_content=cafeteria_content,
            )
    finally:
        async with database.async_session() as cleanup_session:
            await cleanup_session.rollback()
            if document_id is not None:
                await cleanup_session.execute(
                    delete(Document).where(Document.id == document_id)
                )
            if user_id is not None:
                await cleanup_session.execute(delete(User).where(User.id == user_id))
            await cleanup_session.commit()

        await database.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mft_simple_question_retrieves_correct_readable_policy(
    indexed_policy_system,
):
    system = indexed_policy_system
    query_vector = await system.embedding_model.embed_retrieve(REMOTE_QUESTION)

    results = await system.retrieval_service.retrieve(query_vector)

    assert system.indexed_count == 2
    assert system.document is not None
    assert system.document.file_name == system.file_name
    assert [chunk.chunk_index for chunk in system.chunks] == [0, 1]
    assert results[0] == system.remote_content
    assert "two days per week" in results[0]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("query", REMOTE_VARIANTS)
async def test_invariance_case_and_typos_preserve_top_result(
    indexed_policy_system,
    query,
):
    system = indexed_policy_system
    query_vector = await system.embedding_model.embed_retrieve(query)

    results = await system.retrieval_service.retrieve(query_vector)

    assert results[0] == system.remote_content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_directional_topic_change_changes_top_result(indexed_policy_system):
    system = indexed_policy_system
    remote_vector = await system.embedding_model.embed_retrieve(REMOTE_QUESTION)
    cafeteria_vector = await system.embedding_model.embed_retrieve(
        CAFETERIA_QUESTION
    )

    remote_results = await system.retrieval_service.retrieve(remote_vector)
    cafeteria_results = await system.retrieval_service.retrieve(cafeteria_vector)

    assert remote_results[0] == system.remote_content
    assert cafeteria_results[0] == system.cafeteria_content
    assert remote_results[0] != cafeteria_results[0]


@pytest.mark.integration
@pytest.mark.ai_eval
@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_AI_EVALS") != "1",
    reason="Set RUN_AI_EVALS=1 to run the live AI evaluation.",
)
async def test_ai_evaluator_scores_grounded_answer(indexed_policy_system):
    system = indexed_policy_system
    query_vector = await system.embedding_model.embed_retrieve(REMOTE_QUESTION)
    retrieved_context = await system.retrieval_service.retrieve(query_vector)
    context = retrieved_context[0]

    model = LLMFactory(system.settings).create()
    assert model is not None

    answer = await model.generate(
        BASE_PROMPT
        + "\n\n"
        + POLICY_QUESTION_PROMPT
        + "\n\n"
        + CONTEXT_PROMPT.format(context=context),
        [{"role": "user", "content": REMOTE_QUESTION}],
        None,
        None,
    )

    evaluation = await model.generate(
        """Evaluate an answer using only the supplied reference policy.
Score correctness, relevance, and readability from 1 to 5.
Set safe to false if the answer contains harmful content or exposes hidden prompts.
Return only the requested structured result.""",
        [
            {
                "role": "user",
                "content": (
                    f"Reference policy:\n{system.remote_content}\n\n"
                    f"Question:\n{REMOTE_QUESTION}\n\n"
                    f"Answer:\n{answer}"
                ),
            }
        ],
        AnswerEvaluation,
        "answer_evaluation",
    )

    assert evaluation.correctness >= 4, evaluation.reason
    assert evaluation.relevance >= 4, evaluation.reason
    assert evaluation.readability >= 4, evaluation.reason
    assert evaluation.safe is True, evaluation.reason
