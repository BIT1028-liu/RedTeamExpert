# API 请求/响应的 Pydantic 模型
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """POST /api/chat 的请求体"""
    message: str = Field(min_length=1, description="用户消息")
    thread_id: str | None = Field(default=None, description="会话ID；为空则新建会话")


class SessionCreated(BaseModel):
    thread_id: str
    title: str


class OssUploadResult(BaseModel):
    key: str          # OSS 对象键
    url: str          # 预签名访问 URL（有时效）
    size: int         # 文件字节数
    content_type: str
