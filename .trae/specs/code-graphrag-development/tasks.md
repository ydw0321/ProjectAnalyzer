# Tasks - Code-GraphRAG 开发任务清单

## 阶段一：项目初始化

- [ ] Task 1.1: 创建项目目录结构和 requirements.txt
  - [ ] 创建 src/scanner/ 目录
  - [ ] 创建 src/git_analyzer/ 目录
  - [ ] 创建 src/parser/ 目录
  - [ ] 创建 src/llm/ 目录
  - [ ] 创建 src/storage/ 目录
  - [ ] 创建 src/pipeline/ 目录
  - [ ] 创建 config/ 目录
  - [ ] 创建 tests/ 目录
  - [ ] 创建 requirements.txt 依赖文件

- [ ] Task 1.2: 配置 Python 虚拟环境
  - [ ] 创建 venv 虚拟环境
  - [ ] 安装所有依赖包

- [ ] Task 1.3: 创建配置管理模块 (src/config.py)
  - [ ] 实现 Config 类
  - [ ] 配置项目路径、数据库路径、LLM 参数

## 阶段二：核心模块开发

- [ ] Task 2.1: 实现 Git 分析器模块
  - [ ] 创建 src/git_analyzer/__init__.py
  - [ ] 创建 src/git_analyzer/analyzer.py
  - [ ] 实现 GitAnalyzer 类
  - [ ] 实现 get_file_last_commit 方法

- [ ] Task 2.2: 实现 Java AST 解析器模块
  - [ ] 创建 src/parser/__init__.py
  - [ ] 创建 src/parser/java_parser.py
  - [ ] 实现 JavaParser 类
  - [ ] 实现 extract_methods 方法

- [ ] Task 2.3: 实现大模型交互模块
  - [ ] 创建 src/llm/__init__.py
  - [ ] 创建 src/llm/processor.py
  - [ ] 实现 LLMProcessor 类
  - [ ] 实现 generate_summary 方法（支持 Ollama API）

- [ ] Task 2.4: 实现 ChromaDB 向量存储模块
  - [ ] 创建 src/storage/__init__.py
  - [ ] 创建 src/storage/vector_store.py
  - [ ] 实现 KnowledgeBase 类
  - [ ] 实现 add_code_chunk 方法

- [ ] Task 2.5: 实现 Neo4j 图存储模块
  - [ ] 创建 src/storage/graph_store.py
  - [ ] 实现 GraphStore 类
  - [ ] 实现 add_method_node 方法
  - [ ] 实现 add_call_relationship 方法

## 阶段三：主流水线集成

- [ ] Task 3.1: 实现文件扫描器模块
  - [ ] 创建 src/scanner/__init__.py
  - [ ] 创建 src/scanner/scanner.py
  - [ ] 实现 scan_java_files 函数

- [ ] Task 3.2: 创建主入口文件 (main.py)
  - [ ] 整合所有模块
  - [ ] 实现 main() 函数
  - [ ] 添加进度条显示
  - [ ] 添加日志输出

- [ ] Task 3.3: 创建检索验证脚本 (search.py)
  - [ ] 实现基于自然语言的语义检索
  - [ ] 展示检索结果

## 阶段四：测试与优化

- [ ] Task 4.1: 编写单元测试
  - [ ] 测试 GitAnalyzer
  - [ ] 测试 JavaParser
  - [ ] 测试 KnowledgeBase

- [ ] Task 4.2: 集成测试
  - [ ] 使用真实 Java 项目测试
  - [ ] 验证 ChromaDB 存储
  - [ ] 验证 Neo4j 存储（可选）

- [ ] Task 4.3: 性能优化
  - [ ] 添加并行处理支持
  - [ ] 添加缓存机制
  - [ ] 优化大模型调用

---

## Task Dependencies

- Task 1.1 -> Task 1.2 -> Task 1.3
- Task 1.3 -> Task 2.1
- Task 1.3 -> Task 2.2
- Task 1.3 -> Task 2.3
- Task 1.3 -> Task 2.4
- Task 1.3 -> Task 2.5
- Task 2.1 -> Task 3.1
- Task 2.2 -> Task 3.1
- Task 2.3 -> Task 3.2
- Task 2.4 -> Task 3.2
- Task 2.5 -> Task 3.2
- Task 3.1 -> Task 3.2
- Task 3.2 -> Task 3.3
- Task 3.3 -> Task 4.1
- Task 4.1 -> Task 4.2
- Task 4.2 -> Task 4.3
