from datetime import datetime

from models.history import History
from models.news import News
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def add_history(
    db: AsyncSession,
    news_id: int,
    user_id: int,
):
    history = History(news_id=news_id, user_id=user_id, view_time=datetime.now())
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


async def is_news_history(db: AsyncSession, news_id: int, user_id: int):
    query = select(History).where(
        History.news_id == news_id, History.user_id == user_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def refresh_history_time(db: AsyncSession, history: History, new_time: datetime):
    history.view_time = new_time
    await db.commit()
    await db.refresh(history)
    return history


async def get_history_list(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
):
    count_query = select(func.count()).where(History.user_id == user_id)
    count_res = await db.execute(count_query)
    total = count_res.scalar_one()
    query = (
        select(
            News,
            History.view_time.label("history_view_time"),
            History.id.label("history_id"),
        )
        .join(History, History.news_id == News.id)
        .where(History.user_id == user_id)
        .order_by(History.view_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(query)
    return res.all(), total


async def remove_history(db: AsyncSession, history_id: int, user_id: int):
    query = delete(History).where(History.id == history_id, History.user_id == user_id)
    res = await db.execute(query)
    await db.commit()
    return res.rowcount > 0


async def remove_all_history(db: AsyncSession, user_id: int):
    query = delete(History).where(History.user_id == user_id)
    res = await db.execute(query)
    await db.commit()
    return res.rowcount > 0
