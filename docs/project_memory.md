# Code-GraphRAG 项目记忆文档

本文档记录了 ProjectAnalyzer（Code-GraphRAG）项目的完整理解，供后续开发和维护参考。

---

## 一、项目概述

**Code-GraphRAG** 是一个 Python 工具，用于分析 Java 代码库，将解析结果存储到 Neo4j（图数据库）和 ChromaDB（向量数据库），并生成多种维度的架构树（层级树、包结构树、调用链树）。

**核心目标**：将 Java 源代码转化为包含语义搜索（VectorDB）和调用关系（GraphDB）的立体知识库，使开发者能通过自然语言找到相关代码。

---

## 二、技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 语言 | Python | 3.10+ | 主语言 |
| AST 解析 | tree-sitter | ≥0.23.0 | Java 代码抽象语法树解析 |
| Java 语法 | tree-sitter-java | ≥0.21.0 | Java 语法规则 |
| 向量数据库 | ChromaDB | ≥0.5.0 | 存储代码摘要向量，支持语义检索 |
| 图数据库 | Neo4j | ≥5.20.0 | 存储类/方法节点和调用关系图谱 |
| Git 历史 | GitPython | ≥3.1.43 | 提取文件最后修改的 Commit 信息 |
| HTTP 请求 | requests | ≥2.31.0 | 调用 LLM API |
| 进度条 | tqdm | ≥4.66.4 | 流水线执行进度显示 |
| 外部 LLM | Ark API / Ollama | - | 生成代码摘要（可切换） |

---

## 三、项目目录结构

```
ProjectAnalyzer/
├── src/
│   ├── __init__.py
│   ├── config.py                  # 配置中心（路径、数据库、LLM 参数）
│   ├── scanner/
│   │   ├── __init__.py
│   │   └── scanner.py             # Java 文件扫描器
│   ├── git_analyzer/
│   │   ├── __init__.py
│   │   └── analyzer.py            # Git 历史溯源
│   ├── parser/
│   │   ├── __init__.py
│   │   └── java_parser.py         # Java AST 解析器（tree-sitter）
│   ├── llm/
│   │   ├── __init__.py
│   │   └── processor.py           # LLM 摘要生成
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── vector_store.py        # ChromaDB 向量存储
│   │   └── graph_store.py         # Neo4j 图数据库存储
│   └── tree/
│       ├── __init__.py
│       ├── config.py              # 树生成器配置
│       ├── tree_generator.py      # 架构树生成器
│       └── query_service.py       # Neo4j 图查询服务
├── docs/
│   └── project_memory.md          # 本文档（项目记忆）
├── output/                        # 生成的架构树输出（JSON/Mermaid/PlantUML）
├── test_java/                     # 测试用 Java 示例项目
├── main.py                        # 主入口（4 阶段流水线）
├── search.py                      # 语义检索验证脚本
├── plan.md                        # 开发计划文档
├── structure.md                   # 技术架构详细设计文档
├── SPEC.md                        # 功能规格说明书
├── requirements.txt               # 依赖列表
└── test_*.py                      # 单元测试文件
```

---

## 四、主处理流水线

`main.py` 中的 `main()` 函数按以下 4 个阶段顺序执行：

### 阶段1：解析 Java 文件 → Neo4j

- 调用 `scan_java_files(Config.PROJECT_PATH)` 扫描所有 `.java` 文件
- 用 `JavaParser.extract_with_calls(file_path)` 提取：
  - **类节点**（`:Class`）
  - **方法节点**（`:Method`）
  - **内部调用关系**（同类内调用，`type: internal`）
  - **外部调用关系**（跨类调用，`type: external`）
- 调用 `GraphStore` 将节点和关系存入 Neo4j

### 阶段2：查找热点节点（调用其他方法最多的方法）

- 对所有方法进行互相调用计数
- 返回调用其他方法数量 Top 20 的方法（热点节点）

### 阶段3：LLM 摘要 Top5 → ChromaDB

- 对 Top5 热点方法调用 `LLMProcessor.generate_summary()` 生成中文摘要
- 摘要 + 元数据存入 ChromaDB（`KnowledgeBase.add_code_chunk()`）

### 阶段4：生成架构树 → output/ 目录

- 构建 `Layer` 节点（`graph_store.build_layer_nodes_from_classes()`）
- 生成三种架构树并导出多种格式：
  - **层级树**（layer_tree）：按 controller→facade→service→biz→dal 层级组织
  - **包结构树**（package_tree）：按目录/包路径组织
  - **调用链树**（call_chain_tree）：从入口方法出发的调用流

---

## 五、核心模块说明

### 5.1 配置中心（`src/config.py`）

```python
class Config:
    PROJECT_PATH = r"./test_java"        # 目标 Java 项目路径
    CHROMA_DB_PATH = "./chroma_data"     # ChromaDB 本地存储路径
    NEO4J_URI = "bolt://localhost:7687"  # Neo4j 连接地址
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"
    LLM_API_URL = "..."                  # LLM API 地址（支持 Ark API 或 Ollama）
    LLM_API_KEY = "..."                  # API 密钥
    LLM_MODEL = "ark-code-latest"        # 模型名称
    LLM_TIMEOUT = 60                     # 请求超时（秒）
    EXCLUDE_DIRS = {'.git', 'target', 'build', 'node_modules', ...}
    JAVA_FILE_EXT = '.java'
```

### 5.2 Neo4j 图数据模型

**节点类型：**

| 节点标签 | 属性 | 说明 |
|---------|------|------|
| `:Class` | `name`, `file_path` | Java 类 |
| `:Method` | `name`, `class_name`, `file_path` | Java 方法 |
| `:Layer` | `name` | 架构层级（controller/service 等） |
| `:Package` | `name` | 包/目录节点 |
| `:ExternalMethod` | `name` | 未知外部调用的方法 |

**关系类型：**

| 关系 | 属性 | 说明 |
|------|------|------|
| `CALLS` | `type: internal/external/external_unknown` | 方法调用关系 |
| `BELONGS_TO` | - | 方法属于类 |
| `CONTAINS` | - | 层/包包含类/方法 |

### 5.3 ChromaDB 数据模型

**Collection 名称：** `java_code_kb`

| 字段 | 内容 |
|------|------|
| `documents` | 中文摘要文本（用于向量化检索） |
| `metadatas.file_path` | 源文件路径 |
| `metadatas.method_name` | 方法名 |
| `metadatas.class_name` | 所属类名 |
| `metadatas.is_caller_node` | 是否为热点调用节点 |
| `metadatas.calls_count` | 调用其他方法的数量 |
| `metadatas.raw_code` | 原始 Java 代码 |

### 5.4 树生成器配置（`src/tree/config.py`）

```python
class TreeConfig:
    BASE_LAYERS = {'controller', 'service', 'facade', 'biz', 'bl', 'dal', 'dao', 'model', 'entity', 'vo', 'dto'}
    MAX_TREE_DEPTH = 10          # 最大树深度
    MAX_NODE_COUNT = 1000        # 最大节点数
    MAX_CALL_DEPTH = 10          # 调用链最大深度
    DEFAULT_OUTPUT_FORMAT = 'json'
```

层级优先级（数字越小越上层）：controller(1) → facade(2) → service(3) → biz(4) → bl(5) → dal(6) → dao(7) → model(8) → entity(9) → vo(10) → dto(11)

---

## 六、输出格式

所有输出文件位于 `output/` 目录：

| 文件 | 格式 | 内容 |
|------|------|------|
| `output/layer_tree.json` | JSON | 层级架构树 |
| `output/layer_tree.md` | Mermaid | 层级架构树（可视化图表） |
| `output/package_tree.json` | JSON | 包结构树 |
| `output/call_chain_tree.json` | JSON | 调用链树 |
| `output/call_chain_tree.puml` | PlantUML | 调用链树（UML 图） |

---

## 七、测试数据

`test_java/` 目录包含用于单元测试的 Java 示例项目，模拟了典型的 Java 多层架构（controller/service/dao 层），供测试解析、图构建和树生成功能使用。

**测试文件：**

| 测试文件 | 测试内容 |
|---------|---------|
| `test_scanner.py` | 文件扫描器 |
| `test_search.py` | ChromaDB 语义检索 |
| `test_neo4j.py` | Neo4j 图数据库连接和查询 |
| `test_tree.py` | 架构树生成 |
| `test_api.py` | LLM API 调用 |

**运行测试（需要 Neo4j 在 `bolt://localhost:7687` 运行）：**

```bash
pip install -r requirements.txt
python main.py           # 执行完整流水线
python search.py         # 验证语义检索
python test_scanner.py   # 单元测试
```

---

## 八、后续改进方向

1. **并行处理**：对多个 Java 文件并行调用 LLM，加速知识库构建
2. **增量更新**：根据 Git 变更记录只处理新增/修改文件，避免重复处理
3. **AST 增强**：在方法解析时提取更丰富的调用关系（字段访问、构造器调用等）
4. **混合查询（GraphRAG）**：先用 ChromaDB 找入口方法，再用 Neo4j 查上下游调用链，一起输入 LLM 回答
5. **Web UI**：提供可交互的架构树可视化界面
6. **支持更多语言**：扩展 tree-sitter 支持 Python、Go 等语言的代码分析
7. **缓存机制**：缓存 LLM 摘要结果，避免同一方法重复调用 API
