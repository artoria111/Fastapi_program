from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from schemas.base import NewsItemBase


class HistoryAddRequest(BaseModel):
    news_id: int = Field(..., alias="newsId")


class HistoryResponse(BaseModel):
    id: int = Field(..., alias="id")
    news_id: int = Field(..., alias="newsId")
    user_id: int = Field(..., alias="userId")
    view_time: datetime = Field(alias="viewTime")
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class HistoryNewsItemResponse(NewsItemBase):
    history_id: int = Field(..., alias="historyId")
    view_time: datetime = Field(alias="viewTime")
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class HistoryListResponse(BaseModel):
    list: list[HistoryNewsItemResponse]
    total: int
    has_more: bool = Field(alias="hasMore")
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
