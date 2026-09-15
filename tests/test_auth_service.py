from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from models import UserCreate
from services.auth import AuthService

from uuid import uuid4


@pytest.fixture
def password_service():
    return SimpleNamespace(
        get_password_hash=AsyncMock(return_value="hashed-password"),
        verify_password=AsyncMock(),
    )


@pytest.fixture
def token_service():
    return SimpleNamespace(
        create_access_token=AsyncMock(),
        decode=Mock(),
        validate=AsyncMock(),
        deactivate=AsyncMock(),
    )


@pytest.fixture
def user_repo():
    return SimpleNamespace(
        get_by_name=AsyncMock(return_value=None),
        create=AsyncMock(),
    )


@pytest.fixture
def auth_service(password_service, token_service, user_repo):
    return AuthService(
        password_service=password_service,
        token_service=token_service,
        user_repo=user_repo,
    )
    
@pytest.mark.asyncio
async def test_register_user_hashes_password_before_saving(
    auth_service,
    password_service,
    user_repo,
):
    user = UserCreate(
        username="alice",
        password="Password1",
    )

    await auth_service.register_user(user)

    user_repo.get_by_name.assert_awaited_once_with("alice")

    password_service.get_password_hash.assert_awaited_once_with(
        password="Password1"
    )

    user_repo.create.assert_awaited_once_with(
        {
            "username": "alice",
            "hashed_password": "hashed-password",
            "is_active": True,
            "role": "USER",
        }
    )
    
@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_username(
    auth_service,
    password_service,
    user_repo,
):
    user_repo.get_by_name.return_value = SimpleNamespace(
        username="alice"
    )

    user = UserCreate(
        username="alice",
        password="Password1",
    )

    with pytest.raises(HTTPException) as error:
        await auth_service.register_user(user)

    assert error.value.status_code == 400
    assert error.value.detail == "Username already registered"

    password_service.get_password_hash.assert_not_awaited()
    user_repo.create.assert_not_awaited()
    
@pytest.mark.asyncio
async def test_authenticate_rejects_unknown_username(
    auth_service,
    password_service,
    token_service,
    user_repo,
):
    user_repo.get_by_name.return_value = None

    with pytest.raises(HTTPException) as error:
        await auth_service.authenticate_user(
            username="alice",
            password="Password1",
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Not authenticated"

    password_service.verify_password.assert_not_awaited()
    token_service.create_access_token.assert_not_awaited()
    
@pytest.mark.asyncio
async def test_authenticate_rejects_incorrect_password(
    auth_service,
    password_service,
    token_service,
    user_repo,
):
    user_repo.get_by_name.return_value = SimpleNamespace(
        username="alice",
        hashed_password="stored-hash",
    )
    password_service.verify_password.return_value = False

    with pytest.raises(HTTPException) as error:
        await auth_service.authenticate_user(
            username="alice",
            password="WrongPassword1",
        )

    assert error.value.status_code == 401

    password_service.verify_password.assert_awaited_once_with(
        "WrongPassword1",
        "stored-hash",
    )
    token_service.create_access_token.assert_not_awaited()
    
@pytest.mark.asyncio
async def test_authenticate_returns_access_token(
    auth_service,
    password_service,
    token_service,
    user_repo,
):
    user_id = uuid4()

    user_repo.get_by_name.return_value = SimpleNamespace(
        id=user_id,
        username="alice",
        hashed_password="stored-hash",
        is_active=True,
        role="USER",
    )
    password_service.verify_password.return_value = True
    token_service.create_access_token.return_value = "access-token"

    result = await auth_service.authenticate_user(
        username="alice",
        password="Password1",
    )

    assert result == "access-token"

    password_service.verify_password.assert_awaited_once_with(
        "Password1",
        "stored-hash",
    )

    token_service.create_access_token.assert_awaited_once()

    encoded_user = token_service.create_access_token.await_args.args[0]

    assert encoded_user.id == user_id
    assert encoded_user.username == "alice"
    assert encoded_user.is_active is True
    assert encoded_user.role == "USER"


@pytest.mark.asyncio
async def test_get_current_user_returns_user(
    auth_service,
    token_service,
    user_repo,
):
    token_id = uuid4()
    expected_user = SimpleNamespace(id=uuid4(), username="alice")
    token_service.decode.return_value = {
        "sub": str(token_id),
        "username": "alice",
    }
    token_service.validate.return_value = True
    user_repo.get_by_name.return_value = expected_user

    result = await auth_service.get_current_user("access-token")

    assert result is expected_user
    token_service.decode.assert_called_once_with("access-token")
    token_service.validate.assert_awaited_once_with(token_id)
    user_repo.get_by_name.assert_awaited_once_with("alice")


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_token(
    auth_service,
    token_service,
    user_repo,
):
    token_id = uuid4()
    token_service.decode.return_value = {
        "sub": str(token_id),
        "username": "alice",
    }
    token_service.validate.return_value = False

    with pytest.raises(HTTPException) as error:
        await auth_service.get_current_user("access-token")

    assert error.value.status_code == 401
    token_service.validate.assert_awaited_once_with(token_id)
    user_repo.get_by_name.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_username(
    auth_service,
    token_service,
    user_repo,
):
    token_service.decode.return_value = {"sub": str(uuid4())}
    token_service.validate.return_value = True

    with pytest.raises(HTTPException) as error:
        await auth_service.get_current_user("access-token")

    assert error.value.status_code == 401
    user_repo.get_by_name.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_user(
    auth_service,
    token_service,
    user_repo,
):
    token_service.decode.return_value = {
        "sub": str(uuid4()),
        "username": "alice",
    }
    token_service.validate.return_value = True
    user_repo.get_by_name.return_value = None

    with pytest.raises(HTTPException) as error:
        await auth_service.get_current_user("access-token")

    assert error.value.status_code == 401
    user_repo.get_by_name.assert_awaited_once_with("alice")


@pytest.mark.asyncio
async def test_logout_deactivates_token(auth_service, token_service):
    token_id = uuid4()
    token_service.decode.return_value = {
        "sub": str(token_id),
        "username": "alice",
    }

    result = await auth_service.logout("access-token")

    assert result is None
    token_service.decode.assert_called_once_with("access-token")
    token_service.deactivate.assert_awaited_once_with(token_id)
