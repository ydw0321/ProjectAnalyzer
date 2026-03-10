import os


class Config:
    PROJECT_PATH = r"D:\workspace\RI\reins"
    CHROMA_DB_PATH = "./chroma_data"

    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "neo4j"

    LLM_API_URL = "https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions"
    LLM_API_KEY = "f56bc3bc-5b71-4876-930c-87d8189a8909"
    LLM_MODEL = "ark-code-latest"
    LLM_TIMEOUT = 60

    EXCLUDE_DIRS = {'.git', 'target', 'build', 'node_modules', '__pycache__', '.idea', '.vscode'}
    JAVA_FILE_EXT = '.java'
