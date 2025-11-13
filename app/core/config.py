from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    api_version_prefix: str = os.getenv("API_VERSION_PREFIX", "v1")
    global_concurrency: int = int(os.getenv("GLOBAL_CONCURRENCY", 20))
    dispatch_batch_size: int = int(os.getenv("DISPATCH_BATCH_SIZE", 300))
    dispatch_qps_limit: int = int(os.getenv("DISPATCH_QPS_LIMIT", 600))
    retry_max: int = int(os.getenv("RETRY_MAX", 5))
    retry_backoff_base: float = float(os.getenv("RETRY_BACKOFF_BASE", 2.0))
    cache_soft_ttl_s: int = int(os.getenv("CACHE_SOFT_TTL_SEC", 300))
    cache_hard_ttl_s: int = int(os.getenv("CACHE_HARD_TTL_SEC", 900))
    cache_jitter_min: float = float(os.getenv("CACHE_JITTER_MIN", 0.9))
    cache_jitter_max: float = float(os.getenv("CACHE_JITTER_MAX", 1.2))
    log_with_trace_id: bool = os.getenv("LOG_WITH_TRACE_ID", "1") == "1"

    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", 3306))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_db: str = os.getenv("MYSQL_DB", "wecom_ops")
    mysql_charset: str = os.getenv("MYSQL_CHARSET", "utf8mb4")

    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

settings = Settings()
