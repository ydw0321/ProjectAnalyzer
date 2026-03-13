from _bootstrap import bootstrap_project_root

bootstrap_project_root()

from src.scanner.scanner import scan_java_files
from src.config import Config

java_files = scan_java_files(Config.PROJECT_PATH)
print(f"Found {len(java_files)} Java files in {Config.PROJECT_PATH}")
for f in java_files[:5]:
    print(f)
