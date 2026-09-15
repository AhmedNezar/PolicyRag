from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from infrastructure.dependencies import (
    get_auth_service,
    get_conversation_service,
    get_ingestion_service,
)
from main import app
from models import UserRole


class FakeAuthService:
    def __init__(self, user):
        self.user = user
        self.logged_out = False

    async def register_user(self, new_user):
        return self.user

    async def authenticate_user(self, username: str, password: str):
        return "test-access-token"

    async def get_current_user(self, token: str):
        assert token == "test-access-token"
        return self.user

    async def logout(self, token: str):
        assert token == "test-access-token"
        self.logged_out = True


class FakeIngestionService:
    def __init__(self):
        self.uploaded_file_name = None
        self.uploaded_by = None

    async def ingest(self, file, user):
        self.uploaded_file_name = file.filename
        self.uploaded_by = user.id
        return 3


class FakeConversationService:
    def __init__(self):
        self.conversations = []

    async def create_conversation(self, conversation_data):
        conversation = SimpleNamespace(
            id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            **conversation_data,
        )
        self.conversations.append(conversation)
        return conversation

    async def list_conversations(self, skip, take, user_id):
        owned = [
            conversation
            for conversation in self.conversations
            if conversation.user_id == user_id
        ]
        return owned[skip : skip + take]


@pytest.fixture
def test_user():
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        username="alice",
        is_active=True,
        role=UserRole.ADMIN,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.e2e
def test_vertical_document_upload_request(test_user):
    auth_service = FakeAuthService(test_user)
    ingestion_service = FakeIngestionService()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion_service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/file/upload",
                headers={"Authorization": "Bearer test-access-token"},
                files={
                    "file": (
                        "company-policy.pdf",
                        b"fake-pdf-content",
                        "application/pdf",
                    )
                },
            )

        assert response.status_code == 200
        assert response.json() == {"indexed_chunks": 3}
        assert ingestion_service.uploaded_file_name == "company-policy.pdf"
        assert ingestion_service.uploaded_by == test_user.id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.e2e
def test_horizontal_user_conversation_journey(test_user):
    auth_service = FakeAuthService(test_user)
    conversation_service = FakeConversationService()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_conversation_service] = (
        lambda: conversation_service
    )

    try:
        with TestClient(app) as client:
            register_response = client.post(
                "/auth/register",
                json={
                    "username": "alice",
                    "password": "Password1",
                    "role": "admin",
                },
            )
            login_response = client.post(
                "/auth/login",
                data={"username": "alice", "password": "Password1"},
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            create_response = client.post(
                "/conversations/",
                headers=headers,
                json={"title": "Remote Work", "model_type": "test-model"},
            )
            list_response = client.get("/conversations/", headers=headers)
            logout_response = client.post("/auth/logout", headers=headers)

        assert register_response.status_code == 200
        assert register_response.json()["username"] == "alice"
        assert login_response.status_code == 200
        assert login_response.json() == {
            "access_token": "test-access-token",
            "token_type": "Bearer",
        }
        assert create_response.status_code == 201
        assert create_response.json()["title"] == "Remote Work"
        assert list_response.status_code == 200
        assert [item["title"] for item in list_response.json()] == ["Remote Work"]
        assert logout_response.status_code == 200
        assert logout_response.json() == {"message": "Logged out."}
        assert auth_service.logged_out is True
    finally:
        app.dependency_overrides.clear()
