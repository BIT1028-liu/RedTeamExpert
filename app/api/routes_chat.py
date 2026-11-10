# 聊天接口：SSE 流式返回，LangGraph checkpointer 按 thread_id 自动维护多轮上下文
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage

from app.api.schemas import ChatRequest
from app.services.session_service import session_service

router = APIRouter(prefix="/api", tags=["chat"])


def _sse(payload: dict) -> str:
    """编码为一条 SSE 事件（ensure_ascii=False 保证中文原样输出）"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_text(chunk: AIMessageChunk) -> str:
    """兼容 string 和 content-blocks 两种消息内容格式，只取纯文本"""
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        )
    return ""


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    agent = request.app.state.agent

    # 会话管理：没传 thread_id 就新建（以后可改为从登录用户推导）
    is_new = not req.thread_id
    thread_id = req.thread_id or uuid.uuid4().hex
    if is_new:
        await run_in_threadpool(session_service.create, thread_id, req.message[:30])
    else:
        await run_in_threadpool(session_service.touch, thread_id)

    async def event_stream():
        try:
            # 先把 thread_id 告诉前端，前端下次带上它即可续聊
            yield _sse({"type": "meta", "thread_id": thread_id})

            config = {"configurable": {"thread_id": thread_id}}
            inputs = {"messages": [HumanMessage(content=req.message)]}
            # 流式模式 messages：每个模型/工具产生的消息块都会推送 (chunk, metadata)
            async for chunk, meta in agent.astream(inputs, config=config, stream_mode="messages"):
                # 工具执行产生的是 ToolMessage，天然被下面的类型检查排除；
                # 只推送模型的文本增量（工具调用块的 content 为空，也会被 text 判断跳过）
                if not isinstance(chunk, AIMessageChunk):
                    continue
                text = _chunk_text(chunk)
                if text:
                    yield _sse({"type": "token", "content": text})

            yield _sse({"type": "end"})
        except Exception as exc:  # 流式过程中出错也要通知前端，否则界面会一直转圈
            yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 代理缓冲，避免流被攒成一坨
        },
    )
