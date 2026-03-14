import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()


def _get_int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # 使用环境变量覆盖默认值，便于多环境部署与密钥安全管理
    PROJECT_PATH = os.getenv("PROJECT_PATH", r"./fixtures/simple")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_data")

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_WRITE_BATCH_SIZE = _get_int_env("NEO4J_WRITE_BATCH_SIZE", 10000)

    LLM_API_URL = os.getenv(
        "LLM_API_URL",
        "https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions",
    )
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "ark-code-latest")
    LLM_TIMEOUT = _get_int_env("LLM_TIMEOUT", 60)
    LLM_INDEX_MAX_WORKERS = _get_int_env("LLM_INDEX_MAX_WORKERS", 8)

    # 调用关系匹配：启用后优先按 类名+方法名+参数个数 匹配，减少同名/重载污染
    USE_SIGNATURE_MATCH = _get_bool_env("USE_SIGNATURE_MATCH", True)
    # 容差匹配：当精确+唯一回退均失败时，允许参数个数差 ≤ TOLERANT_MAX_DIFF 的方法被选中
    # 适用于 varargs 调用、可选参数等模式；默认关闭以避免误匹配
    SIGNATURE_MATCH_TOLERANT = _get_bool_env("SIGNATURE_MATCH_TOLERANT", False)
    SIGNATURE_TOLERANT_MAX_DIFF = _get_int_env("SIGNATURE_TOLERANT_MAX_DIFF", 1)

    EXCLUDE_DIRS = {'.git', 'target', 'build', 'node_modules', '__pycache__', '.idea', '.vscode'}
    JAVA_FILE_EXT = '.java'
