from typing import Any

from config.cache_conf import get_json_cache, set_cache

CATEGORIES_KEY = "news:categories"
NEWS_LIST_PERFIX = "news_list:"


async def get_cached_categories():
    return await get_json_cache(CATEGORIES_KEY)


async def set_cached_categories(data: list[dict[str, Any]], expire: int = 7200):
    return await set_cache(CATEGORIES_KEY, data, expire)


async def set_cache_news_list(
    category_id: int | None,
    page: int,
    size: int,
    new_list: list[dict[str, Any]],
    expire: int = 1800,
):
    category_part = category_id if category_id is not None else "all"
    key = f"{NEWS_LIST_PERFIX}{category_part}:{page}:{size}"
    return await set_cache(key, new_list, expire)


async def get_cache_news_list(category_id: int | None, page: int, size: int):
    category_id = category_id if category_id is not None else "all"
    key = f"{NEWS_LIST_PERFIX}{category_id}:{page}:{size}"
    return await get_json_cache(key)
