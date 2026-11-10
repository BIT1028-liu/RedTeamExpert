# 阿里云 OSS 服务：上传文件 + 生成预签名访问 URL
# SDK 为 alibabacloud-oss-v2（新版），文档：https://www.alibabacloud.com/help/zh/oss/developer-reference/use-oss-v2-python-sdk
import uuid
from functools import lru_cache

import alibabacloud_oss_v2 as oss

from app.core.config import settings

# 允许上传的扩展名白名单（按需增减）
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".txt", ".md", ".csv", ".xlsx", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class OssConfigError(RuntimeError):
    """OSS 配置缺失时抛出，路由层转成 503 提示用户去 .env 补配置"""


@lru_cache
def get_client() -> oss.Client:
    if not (settings.OSS_REGION and settings.OSS_BUCKET
            and settings.OSS_ACCESS_KEY_ID and settings.OSS_ACCESS_KEY_SECRET):
        raise OssConfigError(
            "OSS 未配置：请在 .env 中填写 OSS_REGION / OSS_BUCKET / OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET"
        )
    cfg = oss.config.Config(
        region=settings.OSS_REGION,
        credentials=oss.credentials.StaticCredentialsProvider(
            access_key_id=settings.OSS_ACCESS_KEY_ID,
            access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
        ),
        # endpoint 留空时由 region 自动推导；私有化/内网场景再显式指定
        endpoint=settings.OSS_ENDPOINT or None,
    )
    return oss.Client(cfg)


def build_object_key(filename: str, prefix: str = "uploads") -> str:
    """用 uuid 重命名，避免中文/重名/路径穿越问题；保留原扩展名"""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}")
    return f"{prefix}/{uuid.uuid4().hex}{ext}"


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """上传二进制内容到 OSS（同步调用，路由层需用 run_in_threadpool 包装）"""
    get_client().put_object(
        oss.PutObjectRequest(
            bucket=settings.OSS_BUCKET,
            key=key,
            body=data,
            content_type=content_type,
        )
    )


def presign_url(key: str, expires: int = 3600) -> str:
    """生成带签名的临时下载链接；Bucket 若为公共读也可直接拼公开 URL"""
    result = get_client().presign(
        oss.GetObjectRequest(bucket=settings.OSS_BUCKET, key=key),
        expires=expires,
    )
    return result.url
