from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NewsItemBase(BaseModel):
    id: int
    title: str
    description: str | None = None
    image: str | None = None
    author: str | None = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: datetime | None = Field(None, alias="publishedTime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
