from datetime import datetime

from config.db_conf import get_db
from crud import history
from fastapi import APIRouter, Depends, HTTPException, Query
from models.users import User
from schemas.base import NewsItemBase
from schemas.history import HistoryAddRequest, HistoryListResponse, HistoryResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/add")
async def add_history(
    data: HistoryAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_history = await history.is_news_history(db, data.news_id, user.id)
    if is_history is not None:
        new_view_time = datetime.now()
        await history.refresh_history_time(db, is_history, new_view_time)
        response_data = HistoryResponse.model_validate(is_history)
        return success_response(message="该新闻已添加过历史", data=response_data)
    res = await history.add_history(db, data.news_id, user.id)
    response_data = HistoryResponse.model_validate(res)
    return success_response(message="添加历史成功", data=response_data)


@router.get("/list")
async def get_history_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await history.get_history_list(db, user.id, page, page_size)
    history_list = [
        {
            **NewsItemBase.model_validate(news).model_dump(),
            "history_id": history_id,
            "view_time": history_view_time,
        }
        for news, history_view_time, history_id in rows
    ]
    has_more = total > page * page_size
    response_data = HistoryListResponse(
        list=history_list, total=total, hasMore=has_more
    )
    return success_response(message="获取历史列表成功", data=response_data)


@router.delete("/delete/{history_id}")
async def delete_history(
    history_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await history.remove_history(db, history_id, user.id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="历史记录不存在",
        )
    return success_response(message="删除历史成功")


@router.delete("/clear")
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await history.remove_all_history(db, user.id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="历史记录不存在",
        )
    return success_response(message="清空历史成功")
