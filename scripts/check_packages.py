from _bootstrap import bootstrap_project_root

bootstrap_project_root()

import os
from src.scanner.scanner import scan_java_files
from src.config import Config

java_files = scan_java_files(Config.PROJECT_PATH)

print("Sample file paths:")
for f in java_files[:10]:
    print(f"  {f}")
    
print("\nAction files:")
action_files = [f for f in java_files if 'action' in f.lower()]
for f in action_files[:5]:
    print(f"  {f}")
