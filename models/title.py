from pydantic import BaseModel, Field

class TitleSummarization(BaseModel):
    title: str = Field(..., description="Title of the conversation based on the sent message.")