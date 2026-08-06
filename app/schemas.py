from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PostResponse(BaseModel):
    id: str
    caption: str | None = None
    url: str
    file_type: str
    file_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaptionUpdate(BaseModel):
    caption: str