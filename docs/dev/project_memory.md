# 项目理解记忆文档

> **说明**：本文档记录对 ProjectAnalyzer（Code-GraphRAG）项目的全面理解，作为后续所有工作的基准文档。
>
> **更新时间**：2026-03-12

---

## 一、项目概述

### 项目名称
**Code-GraphRAG**（智能代码知识库构建工具）

### 核心定位
将本地 Java 代码仓库转化为多层次的智能知识库，支持：
- **语义搜索**：通过向量嵌入（ChromaDB）理解代码语义
- **调用关系图谱**：通过 Neo4j 存储类/方法调用关系
- **架构树可视化**：多视角（层次、包结构、调用链）展示代码结构

### 项目目录（根路径：`/home/runner/work/ProjectAnalyzer/ProjectAnalyzer`）

```
ProjectAnalyzer/
├── src/                          # 主要源代码
│   ├── __init__.py
│   ├── config.py                 # 全局配置（路径、数据库连接、LLM配置）
│   ├── scanner/                  # Java 文件扫描
│   │   └── scanner.py            # 文件发现与过滤（支持 .gitignore 规则）
│   ├── parser/                   # AST 解析
│   │   └── java_parser.py        # 基于 tree-sitter 的 Java 解析器
│   ├── git_analyzer/             # Git 历史分析
│   │   └── analyzer.py           # 提取提交信息、作者、修改记录
│   ├── llm/                      # LLM 集成
│   │   └── processor.py          # 代码摘要生成（调用外部 LLM API）
│   ├── storage/                  # 数据持久化
│   │   ├── vector_store.py       # ChromaDB 向量存储封装
│   │   └── graph_store.py        # Neo4j 图数据库封装
│   └── tree/                     # 架构树生成
│       ├── config.py             # 树生成配置（层次定义、深度限制等）
│       ├── tree_generator.py     # 架构树生成引擎
│       └── query_service.py      # Neo4j 查询服务
├── fixtures/                     # 测试用 Java 示例项目
│   ├── simple/                   # 标准三层架构（controller/service/biz/dal/model）
│   └── ssh/                      # SSH 风格复杂老旧系统（含压测场景）
├── output/                       # 生成的输出文件
│   ├── trees/                    # 架构树产物
│   │   ├── layer_tree.json       # 层次架构树（JSON）
│   │   ├── layer_tree.md         # 层次树（Mermaid 图）
│   │   ├── package_tree.json     # 包结构树（JSON）
│   │   ├── call_chain_tree.json  # 方法调用链树（JSON）
│   │   └── call_chain_tree.puml  # 调用链（PlantUML）
│   ├── quality/                  # 图质量报告
│   │   ├── graph_quality_benchmark.json
│   │   ├── graph_quality_breakdown.json
│   │   └── graph_quality_thresholds.json
│   └── docs/                     # 文档产物
│       ├── architecture_overview.md
│       └── {layer}_overview.md   # 各层摘要文档
├── docs/                         # 项目文档
│   ├── design/                   # 设计规格（稳定）
│   │   ├── SPEC.md               # 详细功能规格说明
│   │   ├── plan.md               # 开发计划文档
│   │   └── structure.md          # 原始架构蓝图
│   └── dev/                      # 开发记录（演进）
│       ├── implementation_progress.md
│       └── project_memory.md     # 本文档（项目理解记忆）
├── main.py                       # 主流程编排（4个阶段）
├── scripts/                      # 辅助脚本目录
│   ├── search.py                 # 语义搜索示例
│   ├── check_packages.py         # 包检查脚本
│   ├── inspect_data.py           # 数据检查脚本
│   └── generate_docs.py          # 文档导出脚本
├── tests/                        # 测试与诊断脚本目录
│   ├── test_scanner.py           # 扫描器测试
│   ├── test_search.py            # 语义搜索测试
│   ├── test_neo4j.py             # Neo4j 测试
│   ├── test_tree.py              # 架构树生成测试
│   └── test_api.py               # LLM API 连通性测试
├── requirements.txt              # Python 依赖列表
├── README.md                     # 项目说明（编码格式）
├── SPEC.md                       # 详细功能规格说明
├── plan.md                       # 开发计划文档
├── structure.md                  # 原始架构蓝图
└── .trae/                        # 任务管理目录（项目规格）
```

---

## 二、技术栈

### 编程语言
- **Python 3.10+**（核心语言）
- **Java**（被分析的目标语言）

### 核心依赖（`requirements.txt`）

| 依赖库 | 版本要求 | 用途 |
|--------|---------|------|
| tree-sitter | >=0.23.0 | AST 解析引擎 |
| tree-sitter-java | >=0.21.0 | Java 语法支持 |
| chromadb | >=0.5.0 | 向量数据库（语义搜索） |
| neo4j | >=5.20.0 | 图数据库驱动 |
| GitPython | >=3.1.43 | Git 历史分析 |
| requests | >=2.31.0 | HTTP 客户端（LLM API 调用） |
| tqdm | >=4.66.4 | 进度条显示 |

### 外部服务依赖
- **Neo4j 数据库**：存储代码图谱（节点：Class、Method、Layer；边：CALLS、BELONGS_TO、CONTAINS）
- **ChromaDB**：向量存储，用于代码嵌入和语义检索
- **LLM API**：远程代码摘要生成服务
  - 主选：Ark（`ark.cn-beijing.volces.com`）
  - 备选：Ollama（本地，`http://localhost:11434`）

---

## 三、核心功能与处理流程

### 主流程（`main.py` 4 个阶段）

```
阶段 1：代码解析与索引
  → 扫描 Java 源文件（过滤 .git、target 等目录）
  → tree-sitter AST 解析：提取类、方法、调用关系、字段、导入
  → 写入 Neo4j：Class 节点、Method 节点、CALLS 关系、BELONGS_TO 关系
  → Git 历史：提取最后提交信息（作者、提交消息）

阶段 2：热点节点分析
  → 识别"热点"方法（被调用频率最高 / 出向调用最多）
  → 输出 Top 20 方法列表

阶段 3：LLM 摘要生成
  → 对 Top 5 热点方法调用 LLM API 生成自然语言摘要
  → 摘要存入 ChromaDB，支持后续语义检索

阶段 4：架构树生成
  → 构建 Layer 节点（controller/facade/service/biz/dal 层）
  → 生成层次树（layer_tree）
  → 生成包结构树（package_tree）
  → 生成调用链树（call_chain_tree）
  → 导出为 JSON、Mermaid 图、PlantUML 格式到 output/ 目录
```

---

## 四、关键模块详解

### 4.1 JavaParser（`src/parser/java_parser.py`）

**核心方法**：
- `extract_methods(file_path)` → `List[Dict]`：提取方法列表（名称、代码）
- `extract_with_calls(file_path)` → `Dict`：完整提取，包含：
  - `classes`：类名列表
  - `methods`：方法信息（名称、所属类、代码）
  - `internal_calls`：同文件内方法调用
  - `external_calls`：跨类方法调用
  - `fields`：字段声明（用于推断跨类调用）
  - `imports`：导入列表（用于类型解析）

**技术细节**：
- 基于 tree-sitter 精确 AST 解析
- 支持分析字段声明推断跨类调用
- 处理 import 语句进行类型解析

### 4.2 GraphStore（`src/storage/graph_store.py`）

**Neo4j 图模式**：
- **节点类型**：`:Class`、`:Method`、`:Layer`、`:Package`、`:ExternalMethod`
- **关系类型**：
  - `(:Method)-[:CALLS {type: 'internal'|'external'|'external_unknown'}]->(:Method)`
  - `(:Method)-[:BELONGS_TO]->(:Class)`
  - `(:Layer)-[:CONTAINS]->(:Class)`
  - `(:Package)-[:CONTAINS]->(:Class)`

**主要操作**：
- 节点增加：`add_class_node`、`add_method_node`、`add_layer_node`、`add_package_node`
- 关系增加：`add_call_relationship`、`add_belongs_to_relationship`、`add_contains_relationship`
- 查询：`get_hot_nodes(limit=50)`、`get_method_count()`、`get_all_layers()`、`get_layer_classes(layer_name)`
- 层次构建：`build_layer_nodes_from_classes()`

### 4.3 KnowledgeBase（`src/storage/vector_store.py`）

**ChromaDB 集合结构**：
- `documents`：LLM 生成的摘要文本（用于语义搜索）
- `metadatas`：包含 `raw_code` 等元数据
- `ids`：chunk 唯一标识符

### 4.4 ArchitectureTreeGenerator（`src/tree/tree_generator.py`）

**树类型**：
- `generate_layer_tree(project_name)` → 按层次（controller/service/biz/dal）组织
- `generate_package_tree(project_name)` → 按目录结构组织
- `generate_call_chain_tree(entry_method, max_depth=10)` → 从入口点展开调用链

**导出格式**：
- `export_tree_json(tree, output_path)` → JSON 文件
- `export_mermaid(tree, output_path)` → Mermaid 图（Markdown）
- `export_plantuml(tree, output_path)` → PlantUML 文件

### 4.5 GraphQueryService（`src/tree/query_service.py`）

**调用链分析**：
- `get_downstream_calls(method_name, max_depth=10)` → 下游调用链
- `get_upstream_callers(method_name, max_depth=10)` → 上游调用者
- `get_data_flow_path(start_method, end_method)` → 两方法间的数据流路径
- `get_entry_methods()` → 获取 controller 层入口方法

---

## 五、配置说明

### 全局配置（`src/config.py`）

```python
class Config:
    PROJECT_PATH = r"./fixtures/simple"    # 目标 Java 项目路径
    CHROMA_DB_PATH = "./chroma_data"       # ChromaDB 存储路径
    NEO4J_URI = "bolt://localhost:7687"    # Neo4j 连接地址
    NEO4J_USER = "neo4j"                   # Neo4j 用户名
    NEO4J_PASSWORD = "password"            # Neo4j 密码
    LLM_API_URL = "..."                    # LLM API 地址
    LLM_API_KEY = "..."                    # LLM API 密钥
    LLM_MODEL = "ark-code-latest"         # LLM 模型名称
    LLM_TIMEOUT = 60                       # LLM 请求超时（秒）
    EXCLUDE_DIRS = {'.git', 'target', 'build', ...}  # 扫描排除目录
    JAVA_FILE_EXT = '.java'               # Java 文件扩展名
```

### 树生成配置（`src/tree/config.py`）

```python
class TreeConfig:
    BASE_LAYERS = {'controller', 'service', 'facade', 'biz', 'bl', 'dal', 'dao', ...}
    SUB_PACKAGE_ENABLED = True            # 启用子包展开
    MAX_SUB_PACKAGE_DEPTH = 3             # 最大子包深度
    MAX_TREE_DEPTH = 10                   # 最大树深度
    MAX_NODE_COUNT = 1000                 # 最大节点数
    QUERY_TIMEOUT = 30                    # 查询超时（秒）
    MAX_CALL_DEPTH = 10                   # 最大调用链深度
    layer_priority = {                    # 层次优先级（输出顺序）
        'controller': 1, 'facade': 2, 'service': 3, 'biz': 4, 'dal': 6, ...
    }
```

---

## 六、输出格式样例

### 层次树 JSON（`output/trees/layer_tree.json`）
```json
{
  "project": "Project",
  "type": "layer_tree",
  "layers": [
    {
      "name": "controller",
      "type": "layer",
      "classes": [
        {
          "name": "OrderController",
          "type": "class",
          "method_count": 5,
          "methods": ["createOrder", "payOrder", ...]
        }
      ]
    }
  ]
}
```

### 调用链树 JSON（`output/trees/call_chain_tree.json`）
```json
{
  "entry": "OrderController.createOrder",
  "type": "call_chain",
  "tree": {
    "name": "createOrder",
    "class": "OrderController",
    "depth": 0,
    "calls": [
      {
        "name": "submitOrder",
        "class": "OrderBiz",
        "call_type": "external",
        "calls": [...]
      }
    ]
  }
}
```

---

## 七、测试数据说明

`fixtures/simple/` 目录包含完整的示例 Java 项目，覆盖典型分层架构：

| 层次 | 文件 |
|------|------|
| controller | OrderController, ProductController, UserController |
| facade | OrderFacade, ProductFacade, UserFacade |
| service | OrderService, PaymentService, ProductService, UserService, InventoryService |
| biz | OrderBiz, ProductBiz, UserBiz |
| dal | OrderDal, ProductDal, UserDal |
| model | Order, Product, User |

---

## 八、运行与测试

### 环境准备
```bash
python -m venv venv
source venv/bin/activate          # Linux/Mac
# 或 venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 运行主流程
```bash
python main.py                    # 执行完整 4 阶段流水线
```

### 单项测试
```bash
python tests/test_scanner.py      # 测试文件扫描
python tests/test_search.py       # 测试语义搜索
python tests/test_neo4j.py        # 测试 Neo4j 图查询
python tests/test_tree.py         # 测试架构树生成
python tests/test_api.py          # 测试 LLM API 连通性
```

### 语义搜索示例
```bash
python scripts/search.py          # 示例：搜索"处理支付请求的逻辑"
```

---

## 九、现有文档列表

| 文件 | 内容 |
|------|------|
| `README.md` | 项目说明（中文编码，含功能特性、结构、快速开始） |
| `SPEC.md` | 详细功能规格（树层次定义、Neo4j 模式扩展、输出格式设计、验收标准） |
| `plan.md` | 开发计划（4 阶段划分、核心类设计、里程碑 M1-M6、风险与应对） |
| `structure.md` | 原始架构蓝图（完整技术架构、代码框架示例、路线图） |
| `docs/project_memory.md` | 本文档（项目理解记忆，作为后续工作基准） |

---

## 十、关键设计决策

1. **分层架构**：代码被自动分类到 controller/facade/service/biz/dal 等标准 Java 分层，通过目录名识别
2. **双存储策略**：Neo4j 存关系结构（支持图遍历），ChromaDB 存语义内容（支持向量检索）
3. **三种树视角**：层次树（业务视角）、包树（代码组织视角）、调用链树（运行时视角）
4. **LLM 集成点**：仅对热点方法（Top 5）生成摘要，避免 LLM 成本过高
5. **tree-sitter 解析**：相比正则解析，准确率更高，支持复杂 Java 语法
6. **子包展开策略**：配置化控制子包是否展开、展开深度，平衡详细度与可读性

---

## 十一、待办与潜在改进方向

基于 `SPEC.md` 和 `plan.md` 中的描述，以下是潜在改进点（仅记录，不做当前任务）：

- [ ] 支持更多 Java 框架注解识别（Spring MVC、MyBatis 等）
- [ ] 增量更新支持（只重新解析变更文件）
- [ ] Web UI 界面展示架构树
- [ ] 支持多语言（目前仅 Java）
- [ ] 更丰富的 LLM 提示词工程优化
- [ ] 调用链可视化交互式探索
- [ ] 批量导出报告功能

---

*本文档由 Copilot Agent 自动生成，基于对项目代码库的全面分析。*
