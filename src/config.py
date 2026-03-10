import os


class Config:
    PROJECT_PATH = r"D:\workspace\YourJavaProject"
    CHROMA_DB_PATH = "./chroma_data"
    LLM_API_URL = "http://localhost:11434/api/generate"
    LLM_MODEL = "qwen2.5:14b"
    LLM_TIMEOUT = 30

    EXCLUDE_DIRS = {'.git', 'target', 'build', 'node_modules', '__pycache__', '.idea', '.vscode'}
    JAVA_FILE_EXT = '.java'
