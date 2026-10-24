# 新闻资讯 App · 后端接口文档

| 项 | 内容 |
|---|---|
| 文档版本 | v1.0 |
| 对应代码 | `master` 分支，提交 `82ce4e4` |
| 服务端 | FastAPI 0.143 + SQLAlchemy 2.0（异步）+ aiomysql + Redis |
| 客户端 | Vue 3 + Vite + Pinia + Vant（`news-headline-frontend`） |
| 基础地址 | `http://127.0.0.1:8000`（本地开发） |
| 数据格式 | `application/json; charset=utf-8` |
| 交互文档 | Swagger UI `/docs`、ReDoc `/redoc`、OpenAPI `/openapi.json` |

---

## 目录

1. [接口约定](#1-接口约定)
2. [认证与令牌](#2-认证与令牌)
3. [统一响应结构](#3-统一响应结构)
4. [错误码](#4-错误码)
5. [分页约定](#5-分页约定)
6. [字段命名与时间格式](#6-字段命名与时间格式)
7. [路由总表](#7-路由总表)
8. [数据模型](#8-数据模型)
9. [接口详情](#9-接口详情)
10. [缓存策略](#10-缓存策略)
11. [前端接入建议](#11-前端接入建议)


---

## 1. 接口约定

| 约定项 | 规则 |
|---|---|
| 协议 / 端口 | HTTP/1.1，默认 `8000`（`uvicorn main:app --reload`） |
| 路由前缀 | 业务接口统一 `/api/{资源}`；`/` 为调试用根路径 |
| 版本策略 | 当前**无版本号**（`/api` 即 v1）。后续不兼容变更应采用 `/api/v2` 或字段级弃用期 |
| 请求体 | 仅支持 JSON；**不支持** `application/x-www-form-urlencoded` 与 `multipart/form-data`（无文件上传能力） |
| 查询参数 | 一律使用 camelCase（如 `categoryId`、`pageSize`、`newsId`），由后端 `Query(alias=...)` 重命名 |
| 请求体字段 | 见各接口；部分 DTO 只接受 camelCase 别名，**不接受** snake_case |
| 响应字段 | **混用** camelCase 与 snake_case，逐接口明确列出，见[第 6 节](#6-字段命名与时间格式) |
| 空数据 | 列表返回 `[]` 而非 `null`；无内容的成功响应 `data` 为 `null` |
| 幂等性 | `GET`/`PUT` 幂等；`DELETE` 单条与清空在“目标不存在”时语义不一致（见附录 A-5） |
| 限流 | 无 |
| 审计日志 | 无（仅 `uvicorn` 访问日志 + `echo=True` 的 SQL 日志） |
| CORS | 允许来源 `http://localhost:5173`，允许凭证，方法/头不限 |

**请求示例（curl）**

```bash
curl -s http://127.0.0.1:8000/api/news/categories
curl -s "http://127.0.0.1:8000/api/news/list?categoryId=1&page=1&pageSize=10"
curl -s -X POST http://127.0.0.1:8000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'
curl -s http://127.0.0.1:8000/api/user/info -H "Authorization: Bearer <token>"
```

---

## 2. 认证与令牌

### 2.1 机制

- 登录/注册成功后由服务端签发令牌，令牌为 **UUID v4 字符串**（36 字符，含连字符），存于 `user_token` 表。
- 有效期 **7 天**（签发时间 + 7×24h），过期后接口返回 `401`。
- 每个用户**同时只保留一个令牌**：再次登录会覆盖旧令牌，旧客户端立即失效（多端登录互踢）。
- 无 JWT、无签名、无刷新令牌、无登出接口；退出登录仅在客户端清除本地令牌。

### 2.2 请求头

```
Authorization: Bearer <token>
```

服务端实现为 `header.replace("Bearer ", "")`，因此**裸 token**（`Authorization: <token>`）同样可用；但 `bearer` 小写不被识别。

### 2.3 鉴权失败

| 场景 | HTTP | code | message |
|---|---|---|---|
| 未携带 `Authorization` 头 | 422 | —（FastAPI 原生结构） | 字段校验错误明细 |
| 令牌不存在 / 已过期 | 401 | 401 | `无效的令牌或已过期的令牌` |

> 客户端应同时处理 `401` 与“缺少请求头导致的 `422`”，前者跳登录页，后者属于调用方式错误。

### 2.4 受保护接口一览

`GET /api/user/info`、`PUT /api/user/update`、`PUT /api/user/password`、`GET /api/favorite/*`、`POST /api/favorite/add`、`DELETE /api/favorite/*`、`GET /api/history/*`、`POST /api/history/add`、`DELETE /api/history/*`。
新闻模块全部公开。

---

## 3. 统一响应结构

### 3.1 业务成功

HTTP 状态码 **200**，响应体固定三字段：

```json
{
  "code": 200,
  "message": "获取新闻分类成功",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 业务码，成功恒为 `200`（与 HTTP 状态一致） |
| `message` | string | 面向用户的中文提示，可直接展示 |
| `data` | object \| array \| null | 业务数据；无数据时为 `null` |

### 3.2 业务失败

HTTP 状态码为 **4xx/5xx**，`code` 与 HTTP 状态码一致，`data` 通常为 `null`：

```json
{
  "code": 404,
  "message": "新闻不存在",
  "data": null
}
```

开发模式（`DEBUG_MODE = True`）下，非业务异常会在 `data` 中附带调试信息：

```json
{
  "code": 500,
  "message": "数据库操作失败，请稍后重试",
  "data": {
    "error_type": "OperationalError",
    "error_detail": "...",
    "traceback": "...",
    "path": "http://127.0.0.1:8000/api/news/list?categoryId=1"
  }
}
```

> 生产部署前必须关闭 `DEBUG_MODE`，否则会泄漏堆栈与 SQL 细节。

### 3.3 异常处理顺序

`HTTPException` → `IntegrityError` → `SQLAlchemyError` → `Exception`（兜底）。前三个由业务/数据库触发，最后一个捕获所有未预期异常并返回 500。

### 3.4 例外：参数校验错误（422）

由 FastAPI 原生校验器返回，**不套用**统一结构：

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "newsId"],
      "msg": "Field required",
      "input": {"news_id": 1}
    }
  ]
}
```

触发场景：必填字段缺失、类型错误、`pageSize > 100`、`page < 1`、`newPassword` 少于 6 位、字段类型为 `str` 却显式传 `null`。

客户端错误提示需兼容两种结构：优先读 `message`，缺失时读 `detail[0].msg`。

---

## 4. 错误码

| HTTP | code | 含义 | 典型 message |
|---:|---:|---|---|
| 200 | 200 | 成功 | 各接口自定义 |
| 400 | 400 | 业务校验失败 / 数据约束冲突 | `用户已存在`、`用户名已存在`、`关联数据不存在`、`数据约束冲突，请检查输入` |
| 401 | 401 | 未认证 / 令牌无效或过期 / 账密错误 | `无效的令牌或已过期的令牌`、`用户名或密码错误` |
| 404 | 404 | 资源不存在 | `新闻不存在`、`收藏记录不存在`、`历史记录不存在`、`用户不存在` |
| 422 | — | 请求参数校验失败（非统一结构） | FastAPI `detail` 数组 |
| 500 | 500 | 服务端内部错误 | `服务器内部错误`、`数据库操作失败，请稍后重试`、`修改密码失败，请稍后再试` |

---

## 5. 分页约定

- `page`：从 **1** 开始，`news/list` 默认 `1` 但**未做下限校验**（传 `0` 或负数会导致 SQL 报错 → 500）；其余列表接口 `page >= 1`。
- `pageSize`：默认 `10`，上限 `100`（超出返回 422）。
- 响应 `data`：

```json
{
  "list": [],
  "total": 128,
  "hasMore": true
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `list` | array | 当前页数据 |
| `total` | int | 满足条件的总记录数 |
| `hasMore` | bool | 是否还有下一页 |

`hasMore` 的实现口径：

- 新闻列表：`(offset + len(list)) < total`（以数据库实际返回条数为准）
- 收藏 / 历史列表：`total > page * pageSize`

两者在“当前页数据被删改”时结果可能不同，客户端应以后者语义理解（还有没有下一页），不要依赖边界值。

---

## 6. 字段命名与时间格式

### 6.1 命名

| 数据来源 | 命名风格 | 示例字段 |
|---|---|---|
| 新闻列表、新闻详情、分类列表（ORM 直接序列化） | snake_case | `category_id`、`publish_time`、`created_at` |
| 经 Pydantic 响应模型序列化（收藏、历史、用户） | camelCase（别名） | `categoryId`、`publishedTime`、`favoriteId`、`historyId`、`userInfo` |
| 请求体 / 查询参数 | camelCase | `newsId`、`pageSize`、`oldPassword` |

> 同一个业务字段在列表接口和收藏/历史接口中**拼写不同**（`publish_time` vs `publishedTime`），这是当前实现问题，见附录 A-1。客户端务必按接口分别取值。

### 6.2 时间

- 类型：ISO 8601 字符串，**不带时区偏移**，语义为服务器本地时间（`Asia/Shanghai`）。
- 示例：`2024-01-01T08:00:00`。
- 来源差异：`favorite.created_at` 使用 UTC 生成（`datetime.utcnow`），比历史/新闻的时间戳早 8 小时，见附录 A-4。

### 6.3 其他

| 类型 | 约定 |
|---|---|
| 布尔 | `true` / `false` |
| 金额 | 无 |
| 枚举 `gender` | `male` / `female` / `unknown` |
| 富文本 | 无 HTML；`content` 为纯文本，段落以 `\n\n` 分隔 |
| 头像 | 仅 URL 字符串，无上传接口 |

---

## 7. 路由总表

| # | 方法 | 路径 | 说明 | 鉴权 | 成功 message |
|---:|---|---|---|:--:|---|
| 1 | GET | `/` | 调试根路径，返回 `{"message":"Hello world"}`（非统一结构） | 否 | — |
| 2 | GET | `/api/news/categories` | 新闻分类列表 | 否 | 获取新闻分类成功 |
| 3 | GET | `/api/news/list` | 新闻列表（按分类分页） | 否 | 获取新闻列表成功 |
| 4 | GET | `/api/news/detail` | 新闻详情（浏览量 +1） | 否 | 获取新闻详情成功 |
| 5 | POST | `/api/user/register` | 注册（成功后自动登录） | 否 | 注册成功 |
| 6 | POST | `/api/user/login` | 登录 | 否 | 登录成功 |
| 7 | GET | `/api/user/info` | 当前用户信息 | 是 | 获取用户信息成功 |
| 8 | PUT | `/api/user/update` | 更新用户资料 | 是 | 更新用户信息成功 |
| 9 | PUT | `/api/user/password` | 修改密码 | 是 | 修改密码成功 |
| 10 | GET | `/api/favorite/check` | 是否已收藏 | 是 | 检查收藏状态成功 |
| 11 | POST | `/api/favorite/add` | 添加收藏 | 是 | 添加收藏成功 |
| 12 | DELETE | `/api/favorite/remove` | 取消收藏 | 是 | 删除收藏成功 |
| 13 | GET | `/api/favorite/list` | 收藏列表（分页） | 是 | 获取收藏列表成功 |
| 14 | DELETE | `/api/favorite/clear` | 清空收藏 | 是 | 清空了 N 条记录 |
| 15 | POST | `/api/history/add` | 记录浏览历史 | 是 | 添加历史成功 / 该新闻已添加过历史 |
| 16 | GET | `/api/history/list` | 浏览历史（分页） | 是 | 获取历史列表成功 |
| 17 | DELETE | `/api/history/delete/{history_id}` | 删除单条历史 | 是 | 删除历史成功 |
| 18 | DELETE | `/api/history/clear` | 清空历史 | 是 | 清空历史成功 |

> 路由参数 `{history_id}` 是**历史记录主键**，不是新闻 ID。列表接口会同时返回 `id`（新闻 ID）与 `historyId`（历史主键），删除时用后者。

---

## 8. 数据模型

### 8.1 Category

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 分类 ID |
| `name` | string | 分类名称（唯一） |
| `sort_order` | int | 排序值，升序 |
| `created_at` | datetime | 仅缓存未命中时返回 |
| `updated_at` | datetime | 仅缓存未命中时返回 |

### 8.2 NewsItem（列表项）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 新闻 ID |
| `title` | string | 标题 |
| `description` | string \| null | 摘要 |
| `image` | string \| null | 封面 URL |
| `author` | string \| null | 作者/来源 |
| `category_id` | int | 分类 ID |
| `views` | int | 浏览量 |
| `publish_time` | datetime | 发布时间 |
| `created_at` | datetime | ORM 直出附带，字段集合不稳定，见附录 A-6 |
| `updated_at` | datetime | 同上 |

### 8.3 NewsDetail

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 新闻 ID |
| `title` | string | 标题 |
| `content` | string | 正文，纯文本，段落以 `\n\n` 分隔 |
| `image` | string \| null | 封面 URL |
| `author` | string \| null | 作者 |
| `publish_time` | datetime | 发布时间 |
| `categoryId` | int | 分类 ID（此处 camelCase） |
| `views` | int | 浏览量（**本次请求自增前**的值） |
| `relatedNews` | array | 相关推荐，最多 5 条，字段同上（`content` 也返回） |

### 8.4 UserInfo

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 用户 ID |
| `username` | string | 用户名（唯一） |

> 当前仅返回以上两字段；昵称、头像、性别、简介、手机号均不返回（附录 A-2）。

### 8.5 FavoriteItem

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | **新闻 ID** |
| `title` / `description` / `image` / `author` / `views` | — | 同 NewsItem |
| `categoryId` | int | 分类 ID |
| `publishedTime` | datetime | 注意拼写为 `publishedTime` |
| `favoriteId` | int | 收藏记录主键 |
| `favoriteTime` | datetime | 收藏时间（UTC 生成，见附录 A-4） |

### 8.6 HistoryItem

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | **新闻 ID**（不是历史主键） |
| `title` / `description` / `image` / `author` / `views` | — | 同 NewsItem |
| `categoryId` | int | 分类 ID |
| `publishedTime` | datetime | 注意拼写为 `publishedTime` |
| `historyId` | int | **历史记录主键**，删除接口用它 |
| `viewTime` | datetime | 最近浏览时间 |

### 8.7 PageResult\<T\>

| 字段 | 类型 | 说明 |
|---|---|---|
| `list` | T[] | 当前页数据 |
| `total` | int | 总条数 |
| `hasMore` | bool | 是否有下一页 |

---

## 9. 接口详情

### 9.1 获取新闻分类

**`GET /api/news/categories`** · 无需鉴权

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|:--:|---|---|
| `skip` | query | int | 否 | 0 | 跳过条数 |
| `limit` | query | int | 否 | 100 | 返回条数上限 |

**成功响应**

```json
{
  "code": 200,
  "message": "获取新闻分类成功",
  "data": [
    {"id": 1, "name": "头条", "sort_order": 1, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"},
    {"id": 2, "name": "社会", "sort_order": 2, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
  ]
}
```

**备注**

- 结果整体缓存于 Redis `news:categories`，TTL 2 小时；缓存命中时不含 `created_at` / `updated_at`。
- 前端只在 7 个分类之外自行追加一个虚拟“更多”项（`id=10`），后端不返回该分类。

---

### 9.2 获取新闻列表

**`GET /api/news/list`** · 无需鉴权

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|:--:|---|---|
| `categoryId` | query | int | **是** | — | 分类 ID；不支持“全部” |
| `page` | query | int | 否 | 1 | 页码，从 1 开始；**未校验下限** |
| `pageSize` | query | int | 否 | 10 | 每页条数，范围 1–100 |

**成功响应**

```json
{
  "code": 200,
  "message": "获取新闻列表成功",
  "data": {
    "list": [
      {
        "id": 1,
        "title": "国家主席发表2024年新年贺词",
        "description": "主席总结过去一年成就，展望未来发展蓝图。",
        "image": "https://picsum.photos/id/100/200/200",
        "author": "新华社",
        "category_id": 1,
        "views": 12500,
        "publish_time": "2024-01-01T08:00:00",
        "created_at": "2024-01-01T08:00:00",
        "updated_at": "2024-01-01T08:00:00"
      }
    ],
    "total": 128,
    "hasMore": true
  }
}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| 缺少 `categoryId` | 422 | `{"detail":[{"loc":["query","categoryId"],"msg":"Field required"}]}` |
| `pageSize > 100` | 422 | 同上 |
| `page <= 0` | 500 | `{"code":500,"message":"服务器内部错误","data":{...}}` |

**备注**：列表不做时间/热度排序（按主键顺序），排序规则未在契约中承诺；如需稳定排序请在接口层明确。

---

### 9.3 获取新闻详情

**`GET /api/news/detail`** · 无需鉴权

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|:--:|---|---|
| `id` | query | int | **是** | — | 新闻 ID |

**成功响应**

```json
{
  "code": 200,
  "message": "获取新闻详情成功",
  "data": {
    "id": 1,
    "title": "国家主席发表2024年新年贺词",
    "content": "第一段正文……\n\n第二段正文……",
    "image": "https://picsum.photos/id/100/200/200",
    "author": "新华社",
    "publish_time": "2024-01-01T08:00:00",
    "categoryId": 1,
    "views": 12500,
    "relatedNews": [
      {
        "id": 2,
        "title": "相关新闻标题",
        "content": "相关新闻正文……",
        "image": "https://picsum.photos/id/101/200/200",
        "author": "人民日报",
        "publish_time": "2024-01-05T09:30:00",
        "categoryId": 1,
        "views": 8900
      }
    ]
  }
}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| `id` 不存在 | 404 | `{"code":404,"message":"新闻不存在","data":null}` |
| 缺少 `id` | 422 | FastAPI `detail` 结构 |

**副作用**：每次成功请求将 `news.views` 加 1；但响应中的 `views` 是自增**前**的值，见附录 A-3。
**相关推荐规则**：同分类、排除自身、按 `views` 降序 + `publish_time` 降序，最多 5 条。

---

### 9.4 注册

**`POST /api/user/register`** · 无需鉴权

**请求体**

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|:--:|---|---|
| `username` | string | 是 | 无长度/格式校验；数据库唯一 | 用户名 |
| `password` | string | 是 | 无长度校验；bcrypt 存储 | 明文密码 |

```json
{"username": "alice", "password": "123456"}
```

**成功响应**（HTTP 200，注册即登录）

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "token": "8f14e45f-ceea-467f-a5b1-1d2a3b4c5d6e",
    "userInfo": {"id": 2, "username": "alice"}
  }
}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| 用户名已存在 | 400 | `{"code":400,"message":"用户已存在","data":null}` |
| 并发注册导致唯一键冲突 | 400 | `{"code":400,"message":"用户名已存在","data":{...调试信息...}}` |
| 字段缺失 | 422 | FastAPI `detail` |

---

### 9.5 登录

**`POST /api/user/login`** · 无需鉴权

**请求体**：同 9.4。

**成功响应**

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "8f14e45f-ceea-467f-a5b1-1d2a3b4c5d6e",
    "userInfo": {"id": 1, "username": "admin"}
  }
}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| 用户名或密码错误 | 401 | `{"code":401,"message":"用户名或密码错误","data":null}` |

**副作用**：签发新令牌并覆盖该用户旧令牌（旧客户端立即 401）。

---

### 9.6 获取当前用户信息

**`GET /api/user/info`** · 需鉴权

**成功响应**

```json
{
  "code": 200,
  "message": "获取用户信息成功",
  "data": {"id": 1, "username": "admin"}
}
```

**失败响应**：401（令牌无效/过期）；缺少 `Authorization` 头时为 422。

---

### 9.7 更新用户资料

**`PUT /api/user/update`** · 需鉴权

**请求体**（全部可选，仅传需要修改的字段）

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|:--:|---|---|
| `nickname` | string | 否 | 长度由数据库限制 50 | 昵称 |
| `avatar` | string | 否 | 长度 255 | 头像 URL，非上传 |
| `gender` | string | 否 | `male` / `female` / `unknown` | 性别 |
| `bio` | string | 否 | 长度 500 | 个人简介 |
| `phone` | string | 否 | 唯一，长度 20 | 手机号 |

```json
{"nickname": "小明", "bio": "这个人很懒", "gender": "unknown"}
```

**成功响应**

```json
{
  "code": 200,
  "message": "更新用户信息成功",
  "data": {"id": 1, "username": "admin"}
}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| 字段传 `null` | 422 | `{"detail":[{"loc":["body","nickname"],"msg":"Input should be a valid string"}]}` |
| 手机号重复 / 其他约束冲突 | 400 | `{"code":400,"message":"用户名已存在",...}`（提示文案不准确，见附录 A-7） |
| 用户不存在 | 404 | `{"code":404,"message":"用户不存在","data":null}` |

**语义限制**：后端以 `exclude_none=True` 更新，**无法把字段清空为空字符串以外的方式**（不能置 `null`）；未传字段保持不变。

---

### 9.8 修改密码

**`PUT /api/user/password`** · 需鉴权

**请求体**

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|:--:|---|---|
| `oldPassword` | string | 是 | — | 旧密码 |
| `newPassword` | string | 是 | **最少 6 位** | 新密码 |

```json
{"oldPassword": "123456", "newPassword": "abcdef"}
```

**成功响应**

```json
{"code": 200, "message": "修改密码成功", "data": null}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| 旧密码错误 | **500** | `{"code":500,"message":"修改密码失败，请稍后再试","data":null}` |
| 新密码少于 6 位 | 422 | FastAPI `detail` |

**备注**：旧密码错误本应返回 400/401，当前实现返回 500，见附录 A-5。修改成功后已签发令牌**不失效**。

---

### 9.9 检查收藏状态

**`GET /api/favorite/check`** · 需鉴权

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|:--:|---|
| `newsId` | query | int | 是 | 新闻 ID |

**成功响应**

```json
{"code": 200, "message": "检查收藏状态成功", "data": {"isFavorite": true}}
```

---

### 9.10 添加收藏

**`POST /api/favorite/add`** · 需鉴权

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|:--:|---|
| `newsId` | int | 是 | 新闻 ID（只接受 camelCase） |

```json
{"newsId": 1}
```

**成功响应**（`data` 为收藏记录，snake_case）

```json
{
  "code": 200,
  "message": "添加收藏成功",
  "data": {"id": 7, "user_id": 2, "news_id": 1, "created_at": "2024-02-02T01:00:00"}
}
```

**失败响应**

| 场景 | HTTP | body |
|---|---|---|
| 重复收藏 | 400 | `{"code":400,"message":"用户名已存在",...}`（提示文案错误，见附录 A-7） |
| `newsId` 不存在 | 400 | `{"code":400,"message":"关联数据不存在",...}` |

**备注**：接口不是幂等的；客户端应先用 9.9 判断或忽略 400 的重复收藏错误。

---

### 9.11 取消收藏

**`DELETE /api/favorite/remove`** · 需鉴权

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|:--:|---|
| `newsId` | query | int | 是 | 新闻 ID |

**成功响应**：`{"code":200,"message":"删除收藏成功","data":null}`

**失败响应**：404 `{"code":404,"message":"收藏记录不存在","data":null}`

---

### 9.12 收藏列表

**`GET /api/favorite/list`** · 需鉴权

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|:--:|---|---|
| `page` | query | int | 否 | 1 | ≥ 1 |
| `pageSize` | query | int | 否 | 10 | 1–100 |

**成功响应**

```json
{
  "code": 200,
  "message": "获取收藏列表成功",
  "data": {
    "list": [
      {
        "id": 1,
        "title": "国家主席发表2024年新年贺词",
        "description": "主席总结过去一年成就。",
        "image": "https://picsum.photos/id/100/200/200",
        "author": "新华社",
        "categoryId": 1,
        "views": 12500,
        "publishedTime": "2024-01-01T08:00:00",
        "favoriteId": 7,
        "favoriteTime": "2024-02-02T01:00:00"
      }
    ],
    "total": 3,
    "hasMore": false
  }
}
```

**排序**：收藏时间倒序。
**注意**：`id` 是新闻 ID；`publishedTime` 不是 `publishTime`。

---

### 9.13 清空收藏

**`DELETE /api/favorite/clear`** · 需鉴权

**成功响应**（无论是否清到数据都返回 200）

```json
{"code": 200, "message": "清空了3条记录", "data": null}
```

**备注**：`message` 内嵌条数，客户端**不要**解析该文案，条数以返回值为准（当前无结构化字段）。

---

### 9.14 记录浏览历史

**`POST /api/history/add`** · 需鉴权

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|:--:|---|
| `newsId` | int | 是 | 新闻 ID（只接受 camelCase） |

```json
{"newsId": 1}
```

**成功响应（首次浏览）**

```json
{
  "code": 200,
  "message": "添加历史成功",
  "data": {"id": 12, "newsId": 1, "userId": 2, "viewTime": "2024-02-02T09:00:00"}
}
```

**成功响应（已存在，刷新浏览时间）**

```json
{
  "code": 200,
  "message": "该新闻已添加过历史",
  "data": {"id": 12, "newsId": 1, "userId": 2, "viewTime": "2024-02-02T09:05:00"}
}
```

**失败响应**：`newsId` 不存在 → 400 `关联数据不存在`；缺字段 → 422。

**语义**：同一用户同一新闻仅保留一条记录，重复调用只更新时间（幂等）。

---

### 9.15 浏览历史列表

**`GET /api/history/list`** · 需鉴权

| 参数 | 位置 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|:--:|---|---|
| `page` | query | int | 否 | 1 | ≥ 1 |
| `pageSize` | query | int | 否 | 10 | 1–100 |

**成功响应**

```json
{
  "code": 200,
  "message": "获取历史列表成功",
  "data": {
    "list": [
      {
        "id": 1,
        "title": "国家主席发表2024年新年贺词",
        "description": "主席总结过去一年成就。",
        "image": "https://picsum.photos/id/100/200/200",
        "author": "新华社",
        "categoryId": 1,
        "views": 12500,
        "publishedTime": "2024-01-01T08:00:00",
        "historyId": 12,
        "viewTime": "2024-02-02T09:05:00"
      }
    ],
    "total": 1,
    "hasMore": false
  }
}
```

**排序**：浏览时间倒序。
**关键**：删除单条时必须使用 `historyId`，**不能**用 `id`。

---

### 9.16 删除单条历史

**`DELETE /api/history/delete/{historyId}`** · 需鉴权

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|:--:|---|
| `historyId` | path | int | 是 | 历史记录主键（非新闻 ID） |

**成功响应**：`{"code":200,"message":"删除历史成功","data":null}`

**失败响应**：404 `{"code":404,"message":"历史记录不存在","data":null}`（记录不存在或不属于当前用户）

---

### 9.17 清空历史

**`DELETE /api/history/clear`** · 需鉴权

**成功响应**：`{"code":200,"message":"清空历史成功","data":null}`

**失败响应**：404 `{"code":404,"message":"历史记录不存在","data":null}` —— 本来就没有记录时也会 404，见附录 A-8。

---

## 10. 缓存策略

| 数据 | Key 格式 | TTL | 实现状态 |
|---|---|---:|---|
| 新闻分类 | `news:categories` | 7200s | 生效 |
| 新闻列表 | `news_list:{categoryId}:{page}:{pageSize}` | 1800s | **读写 Key 不一致，永不命中**（附录 A-9） |
| 新闻详情 | `news:detail:{id}` | — | 文档宣称 5 分钟，**代码未实现** |
| 相关推荐 | `news:related:{id}:{categoryId}` | — | 文档宣称 30 分钟，**代码未实现** |

- Redis 不可用时接口降级为直接查库（异常被吞掉），但**没有连接超时**，Redis 半死不活时请求可能长时间挂起。
- 无缓存失效/主动刷新逻辑，新闻变更后最长 30 分钟（分类为 2 小时）才生效。

---

