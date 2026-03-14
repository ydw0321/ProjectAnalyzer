# Code-GraphRAG

智能代码知识库构建工具。它会扫描 Java 项目、提取类与方法、分析调用关系、生成 LLM 摘要，并将结果写入 ChromaDB 和 Neo4j，最终支持语义检索、调用链追踪和可视化分析。

## 适用环境

- Python 3.10 及以上
- Windows 10/11 可直接使用
- 不需要 Docker
- 不需要 npm；这是一个纯 Python 项目
- Neo4j 为可选外部组件，但调用图、层级树、Dashboard 依赖 Neo4j
- LLM 接口为可选外部组件，但向量知识库构建和问答依赖 LLM

## 功能特性

- 文件扫描：自动扫描 Java 源文件，排除 .git、target、build 等目录
- AST 解析：基于 tree-sitter 提取类、方法和调用关系
- 向量知识库：使用 ChromaDB 持久化方法摘要，支持语义检索
- 图谱存储：使用 Neo4j 存储类、方法和调用边
- 调用链分析：生成层级树、包树、调用链树
- 可视化界面：基于 Streamlit 提供图谱浏览和智能问答

## 目录说明

```text
ProjectAnalyzer/
├── app.py                         # Streamlit 可视化入口
├── main.py                        # 主流水线入口
├── chat_cli.py                    # CLI 问答入口
├── requirements.txt               # Python 依赖
├── .env.example                   # 本地开发环境配置样板
├── .env.production.example        # 生产配置样板
├── setup_windows.bat              # Windows 一键安装依赖
├── run_pipeline_windows.bat       # Windows 启动主流水线
├── run_dashboard_windows.bat      # Windows 启动可视化界面
├── run_cli_windows.bat            # Windows 启动命令行问答
├── scripts/                       # 辅助脚本（检索、导出、排查）
├── tests/                         # 独立测试与诊断脚本
├── src/                           # 核心逻辑
├── ui/                            # Streamlit 面板
├── output/                        # 导出结果
│   ├── trees/                     # 架构树 JSON/PlantUML
│   ├── quality/                   # 图质量报告 JSON
│   └── docs/                      # 各层文档 + 架构概览
└── fixtures/                      # 测试用 Java 示例项目
	├── simple/                    # 标准三层架构样本
	└── ssh/                       # SSH 风格复杂架构样本
```

目录优化原则：

- 根目录只保留主入口、环境文件和启动脚本
- `scripts/` 统一放辅助运行脚本，避免根目录堆满临时工具
- `tests/` 统一放测试和诊断脚本，后续切 pytest 结构也更顺手
- `src/` 与 `ui/` 分别承载核心逻辑和界面逻辑，职责边界更清晰

## 部署顺序

建议严格按下面顺序执行，尤其是在全新 Windows 环境中。

### 1. 安装 Python

- 安装 Python 3.10+，并勾选“Add python.exe to PATH”
- 安装完成后，在终端执行 `python --version` 或 `py -3 --version` 验证

### 2. 一键安装项目依赖

项目根目录已经提供 Windows 一键安装脚本：

```bat
setup_windows.bat
```

这个脚本会自动完成以下动作：

- 创建 `.venv` 虚拟环境
- 升级 `pip`、`setuptools`、`wheel`
- 安装 `requirements.txt` 中的全部 Python 依赖
- 如果根目录不存在 `.env`，自动从 `.env.example` 复制一份

如果你不想双击，也可以在终端中执行：

```bat
setup_windows.bat
```

### 3. 配置 .env

首次执行 `setup_windows.bat` 后，根目录会生成 `.env`。至少需要检查以下配置：

```env
PROJECT_PATH=./fixtures/simple
CHROMA_DB_PATH=./chroma_data

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

LLM_API_URL=https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions
LLM_API_KEY=your_api_key
LLM_MODEL=ark-code-latest
LLM_TIMEOUT=60
USE_SIGNATURE_MATCH=true
```

说明：

- `PROJECT_PATH` 指向你要分析的 Java 项目根目录
- `CHROMA_DB_PATH` 是向量库本地目录，默认即可
- 如果只想先验证依赖安装，暂时可以不填 Neo4j；但 Dashboard 和图谱查询功能不可用
- 如果要执行 LLM 摘要、语义检索、CLI 问答，必须配置有效的 `LLM_API_KEY`

### 4. 视场景安装 Neo4j

因为当前环境没有 Docker，所以完整图谱功能需要在 Windows 本机单独安装 Neo4j，并启动本地服务。

推荐方式：

- 安装 Neo4j Desktop
- 或安装 Neo4j Community Server

安装后确认：

- 监听地址为 `bolt://localhost:7687`
- 用户名与密码与 `.env` 一致

### 5. 按模式启动

#### 模式 A：最小可用模式

适合先在干净环境中验证“代码解析 + LLM 摘要 + 向量检索”。这个模式不依赖 Neo4j 图查询成功。

```bat
run_pipeline_windows.bat --index-all
python scripts/search.py
```

产出：

- ChromaDB 向量库写入到 `chroma_data/`
- 检索可通过 `scripts/search.py` 验证

#### 模式 B：完整模式

适合启用调用图、层级树、包树、Streamlit Dashboard、GraphRAG CLI。

先运行主流水线：

```bat
run_pipeline_windows.bat --index-all --reset-graph
```

再启动界面：

```bat
run_dashboard_windows.bat
```

或启动命令行问答：

```bat
run_cli_windows.bat
```

## 一键部署说明

当前仓库提供的是“依赖一键安装 + 入口一键启动”。

### 一键安装

双击或执行：

```bat
setup_windows.bat
```

### 一键启动主流水线

```bat
run_pipeline_windows.bat --index-all
```

### 一键启动可视化界面

```bat
run_dashboard_windows.bat
```

### 一键启动 CLI 问答

```bat
run_cli_windows.bat
```

注意：

- 仓库内部依赖已经可以一键安装
- Neo4j 仍然是外部服务，无法在无 Docker 的纯脚本环境里代替安装
- 因此“完整一键部署”的前提是：本机已安装 Python 和 Neo4j

## 手动安装方式

如果你不使用批处理脚本，也可以手工安装：

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
copy .env.example .env
```

## 运行入口

### 1. 主流水线

```bash
python main.py
```

常用参数：

- `--index-all`：全量为所有方法生成摘要并写入向量库
- `--index-top N`：仅处理前 N 个热点方法（可与 `--index-all` 或默认模式配合）
- `--neo4j-only`：仅执行 Neo4j 图存储与树导出
- `--vector-only`：仅执行向量摘要索引（增量补齐未索引方法）
- `--graph-only`：兼容旧参数，等价于 `--neo4j-only`
- `--reset-graph`：执行前清空 Neo4j 图数据

推荐分步执行（可随时补跑向量）：

```bash
# 第一步：仅构图（Neo4j）
python main.py --neo4j-only --reset-graph

# 第二步：仅向量索引（全量增量）
python main.py --vector-only --index-all

# 仅索引前 3000 个热点方法（用于提速）
python main.py --vector-only --index-all --index-top 3000

# 需要时补齐未索引方法（例如新增代码后）
python main.py --vector-only --index-all
```

Windows 批处理脚本等价用法：

```bat
run_pipeline_windows.bat --neo4j-only --reset-graph
run_pipeline_windows.bat --vector-only --index-all --index-top 3000
```

### 2. 可视化界面

```bash
python -m streamlit run app.py
```

### 3. 命令行问答

```bash
python chat_cli.py
```

### 4. 向量检索验证

```bash
python scripts/search.py
```

### 5. 文档导出

```bash
python scripts/generate_docs.py
```

## 运行结果

主流水线会按阶段执行：

1. 解析 Java 文件，提取类、方法、调用边
2. 统计热点方法
3. 调用 LLM 生成摘要并写入 ChromaDB
4. 如果 Neo4j 可用，写入图谱并导出树结构到 `output/`

常见输出目录：

- `chroma_data/`：向量库
- `output/trees/layer_tree.json`：层级树
- `output/trees/package_tree.json`：包结构树
- `output/trees/call_chain_tree.json`：调用链树
- `output/trees/call_chain_tree.puml`：PlantUML 调用链图
- `output/quality/`：图质量报告 JSON
- `output/docs/`：各层文档与架构概览

## 配置项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| PROJECT_PATH | 目标 Java 项目路径 | ./fixtures/simple |
| CHROMA_DB_PATH | ChromaDB 存储路径 | ./chroma_data |
| NEO4J_URI | Neo4j 地址 | bolt://localhost:7687 |
| NEO4J_USER | Neo4j 用户名 | neo4j |
| NEO4J_PASSWORD | Neo4j 密码 | 空 |
| LLM_API_URL | LLM 接口地址 | 见 src/config.py |
| LLM_API_KEY | LLM API Key | 空 |
| LLM_MODEL | 模型名称 | ark-code-latest |
| LLM_TIMEOUT | LLM 超时秒数 | 60 |
| LLM_INDEX_MAX_WORKERS | 向量索引并发线程数 | 8 |
| USE_SIGNATURE_MATCH | 是否启用签名匹配 | true |
| SIGNATURE_MATCH_TOLERANT | 是否启用签名容差匹配（灰度） | false |
| SIGNATURE_TOLERANT_MAX_DIFF | 容差匹配允许的参数个数最大差值 | 1 |
| NEO4J_WRITE_BATCH_SIZE | Neo4j 批量写入大小 | 10000 |

### 增量解析模式

使用 `--incremental` 标志可在大型项目中大幅缩短重新分析时间：仅对自上次运行以来发生变更（新增或修改）的 Java 文件重新解析并写入 Neo4j，未变更文件跳过写入。

```bash
python main.py --neo4j-only --incremental
```

文件哈希缓存存储在 `{PROJECT_PATH}/.parse_cache.json`（已加入 `.gitignore`）。

### Spring / MyBatis 注解感知

解析器自动识别 `@Autowired`、`@Resource`、`@Inject` 注解字段（包括多行写法），并将注入字段的声明类型用于调用关系解析，减少 `external_unknown` 边。

同时，`@Mapper` 注解接口会在 Neo4j Class 节点上标记 `is_mapper=true`；`resolve_external_unknown_calls` 的第三趟补链（`mybatis_mapper`，confidence=0.80）会自动将目标为 Mapper 代理方法的 `external_unknown` 边补链到正确的接口方法。

注解规则集在 `config/reflection_patterns.yaml` 中维护，可直接修改无需改代码。

## 图质量基准与关键链配置

图质量脚本支持外部关键链配置，并可自动产出候选链用于人工筛选。

### 1) 生成候选关键链

```bash
python tests/test_graph_quality.py \
	--output output/quality/graph_quality_benchmark.json \
	--critical-chains config/critical_chains.json \
	--suggest-critical-chains-output output/quality/critical_chain_candidates.json \
	--suggest-chain-count 12 \
	--suggest-max-hops 5 \
	--suggest-max-per-core-prefix 2 \
	--suggest-core-prefix-len 3
```

参数说明：

- `--suggest-max-per-core-prefix`：同一核心前缀最多保留数量，用于抑制同构候选链堆叠。
- `--suggest-core-prefix-len`：核心前缀长度（从第 2 跳开始计）。

### 2) 使用项目专用关键链进行基准

仓库内已提供 reins 示例配置：`config/critical_chains.reins.json`。

```bash
python tests/test_graph_quality.py \
	--max-depth 4 \
	--output output/quality/graph_quality_benchmark.reins.quick.json \
	--critical-chains config/critical_chains.reins.json
```

该配置用于替代默认电商示例链，避免在 reins 图上出现“关键链定义命中率为 0” 的误判。

## 常见问题

### 1. 是否需要 npm？

不需要。当前仓库没有前端构建步骤，UI 由 Streamlit 提供。

### 2. 没有 Neo4j 能不能运行？

可以运行部分能力：

- 可以做代码解析
- 可以生成 LLM 摘要和向量检索
- 不可用调用图查询、层级树导出、Dashboard 图谱浏览

### 3. 没有 LLM Key 能不能运行？

可以执行不依赖 LLM 的图谱流程：

```bash
python main.py --graph-only
```

但无法构建完整向量知识库，也无法使用问答能力。

### 4. Windows 上推荐怎么启动？

推荐顺序：

1. 执行 `setup_windows.bat`
2. 修改 `.env`
3. 如需完整功能，先安装并启动 Neo4j
4. 执行 `run_pipeline_windows.bat --index-all --reset-graph`
5. 执行 `run_dashboard_windows.bat`

## 依赖清单

- tree-sitter >= 0.23.0
- tree-sitter-java >= 0.21.0
- chromadb >= 0.5.0
- neo4j >= 5.20.0
- GitPython >= 3.1.43
- requests >= 2.31.0
- tqdm >= 4.66.4
- streamlit >= 1.35.0
- streamlit-agraph >= 0.0.45
- python-dotenv >= 1.0.1
