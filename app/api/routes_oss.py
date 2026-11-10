# OSS 文件上传接口
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.schemas import OssUploadResult
from app.services import oss_service
from app.services.oss_service import OssConfigError

router = APIRouter(prefix="/api/oss", tags=["oss"])


@router.post("/upload", response_model=OssUploadResult)
async def upload(file: UploadFile):
    """上传文件到 OSS，返回对象键和 1 小时有效的预签名 URL"""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    if len(data) > oss_service.MAX_FILE_SIZE:
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
    return {"key": key, "url": url, "expires": expires}
