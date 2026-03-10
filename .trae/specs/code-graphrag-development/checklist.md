# Checklist - Code-GraphRAG 验收清单

## 阶段一：项目初始化

- [x] 项目目录结构创建完整（src/scanner, src/git_analyzer, src/parser, src/llm, src/storage, src/pipeline, config, tests）
- [x] requirements.txt 包含所有依赖（tree-sitter, tree-sitter-java, chromadb, neo4j, GitPython, requests, tqdm）
- [x] Python 虚拟环境创建成功
- [x] 依赖包安装成功，无报错
- [x] Config 类实现，包含 PROJECT_PATH、CHROMA_DB_PATH、LLM_API_URL、LLM_MODEL

## 阶段二：核心模块

- [x] GitAnalyzer 类实现 get_file_last_commit 方法
- [x] GitAnalyzer 能正确处理非 Git 仓库场景
- [x] JavaParser 类实现 extract_methods 方法
- [x] JavaParser 能提取方法名和完整代码块
- [x] LLMProcessor 类实现 generate_summary 方法
- [x] LLMProcessor 支持 Ollama API 调用格式
- [x] LLMProcessor 包含超时和错误处理机制
- [x] KnowledgeBase 类实现 add_code_chunk 方法
- [x] ChromaDB 数据持久化到本地目录
- [x] GraphStore 类实现 add_method_node 方法
- [x] GraphStore 类实现 add_call_relationship 方法

## 阶段三：主流水线

- [x] scan_java_files 函数能扫描指定目录
- [x] scan_java_files 排除 .git、target 等目录
- [x] main.py 能完整执行流水线
- [x] 进度条正常显示
- [x] 日志输出清晰
- [x] search.py 能执行语义检索
- [x] 检索结果包含摘要、文件路径、原始代码

## 阶段四：测试与优化

- [ ] GitAnalyzer 单元测试通过
- [ ] JavaParser 单元测试通过
- [ ] KnowledgeBase 单元测试通过
- [ ] 使用真实 Java 项目验证完整流程
- [ ] ChromaDB 检索功能正常
- [ ] Neo4j 图关系创建正常（可选）

## 功能验收

- [ ] 能成功解析 Java 源文件中的方法
- [ ] 能调用本地大模型生成中文摘要
- [ ] 能将数据存入 ChromaDB 向量库
- [ ] 能通过自然语言查询找到相关代码
- [ ] 错误处理完善，不因单个文件错误中断流程

## 文档验收

- [x] README.md 包含使用说明
- [x] 代码注释清晰
- [x] 配置文件易于修改
