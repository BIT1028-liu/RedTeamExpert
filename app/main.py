# FastAPI 入口：uv run uvicorn app.main:app --reload --port 8000
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.RedTeamExpert import build_agent
from app.api import routes_chat, routes_oss, routes_sessions
from app.core.config import settings

CHECKPOINT_DB = Path(__file__).resolve().parents[1] / "rescources" / "checkpoints.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时装配 checkpointer 和 Agent，关闭时释放 SQLite 连接"""
    # rescources/ 里只有被 .gitignore 排除的 .db 文件，git 不追踪空目录，
    # 新 clone 的仓库里该目录不存在，SQLite 无法在缺失的父目录下建库，需先创建
    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as checkpointer:
        await checkpointer.setup()  # 建表（首次运行时）
        # 把带 checkpointer 的 Agent 挂到 app.state，所有路由通过 request.app.state.agent 使用
        app.state.agent = build_agent(checkpointer=checkpointer)
        yield


app = FastAPI(title="RedTeamExpert API", lifespan=lifespan)

# CORS：允许前端开发服务器跨域调用（含 SSE 流式响应）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_chat.router)
app.include_router(routes_sessions.router)
app.include_router(routes_oss.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    """浏览器访问根路径时自动跳转到接口文档页"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
