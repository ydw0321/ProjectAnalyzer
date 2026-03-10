# Code-GraphRAG 开发计划

## 一、项目概述

基于 `structure.md` 需求文档，开发一个**智能代码知识库构建工具**，将本地代码仓库（Java项目）转化为包含语义搜索（ChromaDB）和调用关系（Neo4j）的立体知识库。

---

## 二、技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Source Scanner │ -> │  Git Analyzer   │ -> │  AST Parser     │
│  (文件扫描)      │    │  (Git历史溯源)   │    │  (tree-sitter)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ChromaDB       │ <- │  LLM Processor  │    │  Neo4j          │
│  (向量存储)      │    │  (大模型生成摘要) │    │  (图关系存储)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 三、开发阶段规划

### 阶段一：项目初始化 (1-2天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 1.1 | 创建 Python 虚拟环境 | P0 |
| 1.2 | 配置 `requirements.txt` 依赖 | P0 |
| 1.3 | 创建项目目录结构 | P1 |
| 1.4 | 配置日志系统 | P1 |

**目录结构规划：**
```
ProjectAnalyzer/
├── src/
│   ├── scanner/          # 文件扫描模块
│   ├── git_analyzer/    # Git历史分析模块
│   ├── parser/          # AST解析模块
│   ├── llm/             # 大模型交互模块
│   ├── storage/         # 存储引擎模块
│   │   ├── vector_store.py   # ChromaDB
│   │   └── graph_store.py    # Neo4j
│   └── pipeline/        # 主流水线
├── config/              # 配置文件
├── tests/               # 单元测试
├── main.py              # 入口文件
└── requirements.txt
```

### 阶段二：核心模块开发 (4-5天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 2.1 | 实现 GitAnalyzer 类 | P0 |
| 2.2 | 实现 JavaParser (tree-sitter) | P0 |
| 2.3 | 实现 LLMProcessor 类 | P0 |
| 2.4 | 实现 ChromaDB 存储 | P0 |
| 2.5 | 实现 Neo4j 存储 | P1 |

### 阶段三：主流水线集成 (2-3天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 3.1 | 编排主处理流程 | P0 |
| 3.2 | 添加进度条和日志 | P1 |
| 3.3 | 配置管理 (Config类) | P0 |
| 3.4 | 错误处理和重试机制 | P1 |

### 阶段四：测试与优化 (2-3天)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| 4.1 | 单元测试编写 | P1 |
| 4.2 | 使用测试Java项目验证 | P0 |
| 4.3 | 性能优化 (并行处理) | P2 |
| 4.4 | 检索验证脚本 | P1 |

---

## 四、核心类设计

### Config 配置中心
- `PROJECT_PATH`: 目标Java项目路径
- `CHROMA_DB_PATH`: 向量库存储路径
- `LLM_API_URL`: 大模型API地址
- `LLM_MODEL`: 模型名称

### GitAnalyzer
```python
class GitAnalyzer:
    def get_file_last_commit(file_path) -> dict
```

### JavaParser
```python
class JavaParser:
    def extract_methods(file_path) -> list[dict]
    def extract_classes(file_path) -> list[dict]
```

### LLMProcessor
```python
class LLMProcessor:
    def generate_summary(method_name, code, git_info) -> str
```

### KnowledgeBase (ChromaDB)
```python
class KnowledgeBase:
    def add_code_chunk(chunk_id, summary, code, metadata)
    def search(query, top_k) -> list
```

### GraphStore (Neo4j)
```python
class GraphStore:
    def add_method_node(method_info)
    def add_call_relationship(source, target)
    def get_method_neighbors(method_name) -> list
```

---

## 五、里程碑

| 里程碑 | 完成标准 |
|--------|----------|
| M1 | 环境搭建完成，可运行 `python main.py` |
| M2 | 核心模块开发完成，成功解析Java文件 |
| M3 | 集成大模型，成功生成代码摘要 |
| M4 | ChromaDB 存储完成，可执行语义检索 |
| M5 | Neo4j 图关系存储完成 |
| M6 | 完整流水线验证通过 |

---

## 六、待确认事项

1. **目标Java项目路径**: 需要用户提供一个真实的Java项目用于测试
2. **大模型服务**: 确认使用 Ollama 还是其他兼容 OpenAI 的接口
3. **Neo4j 部署**: 确认是否需要配置 Neo4j（Docker 或本地安装）
4. **项目规模**: 是否有特定的代码规模要求（如方法数、文件数上限）

---

## 七、风险与对策

| 风险 | 对策 |
|------|------|
| tree-sitter Java 解析失败 | 降级到简单正则匹配 |
| 大模型 API 超时 | 添加重试机制和超时配置 |
| ChromaDB 版本兼容 | 锁定版本号 0.4.24 |
| Neo4j 连接失败 | 跳过图存储，仅保留向量存储 |
