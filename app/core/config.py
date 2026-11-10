# 统一的环境变量加载与配置读取
# 所有 .env 中的配置都从这里取，避免各模块重复 load_dotenv()
import os

from dotenv import find_dotenv, load_dotenv

# 向上自动查找项目根目录的 .env（无论从哪个目录启动都能找到）
load_dotenv(find_dotenv())


class Settings:
    """从环境变量读取配置；新增配置项时在这里加一行即可"""

    # 智谱 GLM
    ZHIPU_BASE_URL: str = os.getenv("ZHIPU_BASE_URL", "")
    YOUR_API_KEY: str = os.getenv("YOUR_API_KEY", "")

    # Tavily（langchain-tavily 会自动读 TAVILY_API_KEY，这里留作备用）
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # 阿里云 OSS
    OSS_REGION: str = os.getenv("OSS_REGION", "")            # 例如 cn-hangzhou
    OSS_BUCKET: str = os.getenv("OSS_BUCKET", "")
    OSS_ACCESS_KEY_ID: str = os.getenv("OSS_ACCESS_KEY_ID", "")
    OSS_ACCESS_KEY_SECRET: str = os.getenv("OSS_ACCESS_KEY_SECRET", "")
    # 可选：外网 endpoint，例如 oss-cn-hangzhou.aliyuncs.com；留空则由 region 推导
    OSS_ENDPOINT: str = os.getenv("OSS_ENDPOINT", "")

    # 前端开发服务器地址（CORS 白名单），多个用逗号分隔
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")


settings = Settings()
