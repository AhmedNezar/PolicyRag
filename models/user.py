from pydantic import BaseModel, Field, AfterValidator, ConfigDict, validate_call
from typing import Annotated
from datetime import datetime
from uuid import UUID

@validate_call
def validate_username(value: str) -> str:
    if not value.isalnum():
        raise ValueError("Username must be alphanumeric")
    return value

@validate_call
def validate_password(value: str) -> str:
    validators = [
        (
            lambda x: any(char.isdigit() for char in x),
            "Password must contain at least one digit."
        ),
        
        (
            lambda x: any(char.isupper() for char in x),
            "Password must contain at least one uppercase letter."
        ),
        
        (
            lambda x: any(char.islower() for char in x),
            "Password must contain at least one lowercase letter."
        )
    ]
    
    for validator, error_message in validators:
        if not validator(value):
            raise ValueError(error_message)
    
    return value

ValidUsername = Annotated[str, Field(min_length=3, max_length=20), AfterValidator(validate_username)]
ValidPassword = Annotated[str, Field(min_length=8, max_length=64), AfterValidator(validate_password)]

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    username: ValidUsername
    is_active: bool = True
    role: str = "USER"
    
class UserCreate(UserBase):
    password: ValidPassword
    
class UserInDB(UserBase):
    hashed_password: str
    
class UserEncode(UserBase):
    id: UUID