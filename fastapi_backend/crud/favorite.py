from models.favorite import Favorite
from models.news import News
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def is_news_favorite(db: AsyncSession, news_id: int, user_id: int):
    query = select(Favorite).where(
        Favorite.news_id == news_id, Favorite.user_id == user_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def add_news_favorite(db: AsyncSession, news_id: int, user_id: int):
    favorite = Favorite(news_id=news_id, user_id=user_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    return favorite


async def remove_news_favorite(db: AsyncSession, news_id: int, user_id: int):
    query = delete(Favorite).where(
        Favorite.news_id == news_id, Favorite.user_id == user_id
    )
    res = await db.execute(query)
    await db.commit()
    return res.rowcount > 0


async def get_favorite_list(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
):
    count_query = select(func.count()).where(Favorite.user_id == user_id)
    count_res = await db.execute(count_query)
    total = count_res.scalar_one()
    query = (
        select(
            News,
            Favorite.created_at.label("favorite_time"),
            Favorite.id.label("favorite_id"),
        )
        .join(Favorite, Favorite.news_id == News.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(query)
    return res.all(), total


async def remove_all_favorite(db: AsyncSession, user_id: int):
    query = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(query)
    await db.commit()
    return result.rowcount or 0
