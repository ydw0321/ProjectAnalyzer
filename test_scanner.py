import os
import sys
sys.path.insert(0, r"D:\workspace\ProjectAnalyzer")

from src.scanner.scanner import scan_java_files

project_path = r"D:\workspace\YourJavaProject"
java_files = scan_java_files(project_path)
print(f"Found {len(java_files)} Java files")
for f in java_files[:5]:
    print(f)
