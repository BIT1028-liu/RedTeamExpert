# OSS 文件上传接口
from alibabacloud_oss_v2.exceptions import BaseError as OssBaseError
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.schemas import OssUploadResult
from app.services import oss_service
from app.services.oss_service import OssConfigError

router = APIRouter(prefix="/api/oss", tags=["oss"])


@router.post("/upload", response_model=OssUploadResult)
async def upload(file: UploadFile):
    """上传文件到 OSS，返回对象键和 1 小时有效的预签名 URL"""
    # 先按声明大小拦截超大文件，避免把整个文件读进内存后才发现超限
    if file.size is not None and file.size > oss_service.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件超过 10MB 限制")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    if len(data) > oss_service.MAX_FILE_SIZE:  # 兜底：声明大小缺失时仍按实际内容校验
        raise HTTPException(status_code=413, detail="文件超过 10MB 限制")

    try:
        key = oss_service.build_object_key(file.filename or "unnamed")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        # oss SDK 是同步阻塞调用，丢进线程池避免卡住事件循环
        await run_in_threadpool(
            oss_service.upload_bytes, key, data, file.content_type or "application/octet-stream"
        )
        url = await run_in_threadpool(oss_service.presign_url, key)
    except OssConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OssBaseError as exc:
        # 密钥错误、网络失败等 SDK 异常统一转 502，避免裸 500 且前端拿不到可读信息
        raise HTTPException(status_code=502, detail=f"OSS 服务异常: {exc}")

    return OssUploadResult(
        key=key, url=url, size=len(data), content_type=file.content_type or "application/octet-stream"
    )


@router.get("/download-url")
async def download_url(key: str, expires: int = 3600):
    """按对象键获取新的预签名下载链接（旧链接过期后前端调这个续期）"""
    # 有效期钳制在 1 分钟 ~ 7 天，防止超大值/负数导致 OSS 签名接口报 500
    expires = max(60, min(expires, 604800))
    try:
        url = await run_in_threadpool(oss_service.presign_url, key, expires)
    except OssConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OssBaseError as exc:
        raise HTTPException(status_code=502, detail=f"OSS 服务异常: {exc}")
    return {"key": key, "url": url, "expires": expires}
