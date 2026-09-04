from fastapi import APIRouter, Depends
from infrastructure.dependencies import AuthServiceDep
from typing import Annotated
from .schemas.User import UserOut
from .schemas.Token import TokenOut
from models.user import UserCreate
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from entities import User
from exceptions import UnauthorizedException

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()
LoginFormDep = Annotated[OAuth2PasswordRequestForm, Depends()]
AuthHeaderDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]

@auth_router.post("/register")
async def register_user(new_user: UserCreate, auth_service: AuthServiceDep) -> UserOut:
    user = await auth_service.register_user(new_user)
    return UserOut.model_validate(user)
    
@auth_router.post("/login")
async def login(form_data: LoginFormDep, auth_service: AuthServiceDep) -> TokenOut:
    token = await auth_service.authenticate_user(username=form_data.username, password=form_data.password)
    return TokenOut(access_token=token)

@auth_router.post("/logout")
async def logout(credentials: AuthHeaderDep, auth_service: AuthServiceDep):
    await auth_service.logout(token=credentials.credentials)
    return {"message": "Logged out."}

async def get_current_user(credentials: AuthHeaderDep, auth_service: AuthServiceDep):
    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException
    if not (token := credentials.credentials):
        raise UnauthorizedException
        
    print("Getting current user")
    return await auth_service.get_current_user(token)

AuthenticateUserDep = Annotated[User, Depends(get_current_user)]