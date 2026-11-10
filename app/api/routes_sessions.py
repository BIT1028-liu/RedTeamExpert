# 会话管理接口：列表 / 新建 / 历史消息 / 删除
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.services.session_service import session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions():
    """会话列表（按最近活跃排序），用于渲染前端侧边栏"""
    return await run_in_threadpool(session_service.list)


@router.post("")
async def create_session():
    """新建空会话，返回 thread_id；前端之后把消息连着这个 thread_id 发给 /api/chat"""
    import uuid
    thread_id = uuid.uuid4().hex
    return await run_in_threadpool(session_service.create, thread_id, "新会话")


@router.get("/{thread_id}/messages")
async def get_history(thread_id: str, request: Request):
    """从 checkpointer 读取某个会话的完整历史（human/ai 消息，跳过 tool 中间消息）"""
    agent = request.app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    state = await agent.aget_state(config)
    messages = (state.values or {}).get("messages", [])

    result = []
    for m in messages:
        if m.type == "tool":
            continue
        content = m.content
        if isinstance(content, list):
            content = "".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        if not content:
            continue
        result.append({
            "role": "user" if m.type == "human" else "assistant",
            "content": content,
        })
    return {"thread_id": thread_id, "messages": result}


@router.delete("/{thread_id}")
async def delete_session(thread_id: str, request: Request):
    """删除会话：清掉注册表记录 + checkpointer 里该线程的全部 checkpoint"""
    deleted = await run_in_threadpool(session_service.delete, thread_id)
    try:
        # 注意：adelete_thread 只接受 thread_id 字符串（不是 config 字典），
        # 传错会导致 DELETE 条件永不匹配，静默失败、对话内容残留在 checkpoints.db
        await request.app.state.agent.checkpointer.adelete_thread(thread_id)
    except AttributeError:
        pass  # 旧版 checkpointer 没有 adelete_thread，忽略即可
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"deleted": True}
