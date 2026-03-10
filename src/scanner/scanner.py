import os
from src.config import Config


def scan_java_files(project_path):
    java_files = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in Config.EXCLUDE_DIRS]
        for file in files:
            if file.endswith(Config.JAVA_FILE_EXT):
                java_files.append(os.path.join(root, file))
    return java_files
