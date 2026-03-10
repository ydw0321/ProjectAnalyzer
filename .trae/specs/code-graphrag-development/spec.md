# Code-GraphRAG 智能代码知识库构建工具规格文档

## Why

当前开发者面临代码检索困难的问题：传统的关键词搜索无法理解代码语义，无法通过自然语言提问找到相关代码片段。本项目旨在构建一个**语义化的代码知识库工具**，将 Java 源代码转化为包含语义向量和调用关系的立体知识库，使开发者能够用自然语言提问即可找到相关代码。

## What Changes

- 新增 **Code-GraphRAG** 核心系统，实现代码到知识库的自动化转换
- 实现基于 tree-sitter 的 Java AST 解析器，支持类和方法级别的代码切分
- 集成 ChromaDB 向量数据库，存储代码摘要的语义向量
- 集成 Neo4j 图数据库，存储代码调用关系图谱
- 实现本地大模型（Ollama）集成，自动生成代码摘要

## Impact

- Affected specs: 无（全新功能）
- Affected code: 新增 `src/` 目录，包含 scanner、git_analyzer、parser、llm、storage、pipeline 等模块

---

## ADDED Requirements

### Requirement: 文件扫描能力

系统 SHALL 支持遍历指定目录，扫描所有 Java 源文件（.java），并按 .gitignore 规则过滤非必要文件。

#### Scenario: 扫描 Java 项目
- **GIVEN** 配置了有效的项目路径 `D:\workspace\YourJavaProject`
- **WHEN** 执行扫描操作
- **THEN** 返回所有 .java 文件的绝对路径列表，排除 .git、target 等目录

---

### Requirement: Git 历史溯源

系统 SHALL 支持提取 Java 文件的最后修改提交信息，包括作者、提交消息和提交时间。

#### Scenario: 获取文件 Git 信息
- **GIVEN** 项目是一个有效的 Git 仓库
- **WHEN** 传入任意 .java 文件路径
- **THEN** 返回包含 author、message、date 的字典

#### Scenario: 非 Git 仓库
- **GIVEN** 项目目录不是 Git 仓库
- **WHEN** 尝试获取 Git 信息
- **THEN** 返回默认信息 {"author": "Unknown", "message": "No Git", "date": "Unknown"}

---

### Requirement: Java AST 解析

系统 SHALL 支持使用 tree-sitter 解析 Java 源文件，提取所有方法声明及其完整代码块。

#### Scenario: 解析单个 Java 文件
- **GIVEN** 一个有效的 .java 文件路径
- **WHEN** 执行 extract_methods 操作
- **THEN** 返回方法列表，每个元素包含 name 和 code 字段

---

### Requirement: 大模型摘要生成

系统 SHALL 支持调用本地大模型（Ollama），基于方法代码和 Git 历史生成自然语言摘要。

#### Scenario: 生成代码摘要
- **GIVEN** 方法名、源代码、Git 信息
- **WHEN** 调用 generate_summary 函数
- **THEN** 返回不超过 200 字的中文摘要，包含核心功能和外部依赖

#### Scenario: 大模型调用失败
- **GIVEN** 大模型服务不可用或返回错误
- **WHEN** 调用 generate_summary 函数
- **THEN** 返回错误信息字符串，不中断主流程

---

### Requirement: ChromaDB 向量存储

系统 SHALL 支持将代码摘要和原始代码持久化存储到 ChromaDB，支持语义检索。

#### Scenario: 存储代码块
- **GIVEN** chunk_id、summary、code、metadata
- **WHEN** 调用 add_code_chunk 方法
- **THEN** 数据成功写入 ChromaDB，原始代码存储在 metadata 中

#### Scenario: 语义检索
- **GIVEN** 自然语言查询
- **WHEN** 调用 collection.query 方法
- **THEN** 返回最相关的代码块列表

---

### Requirement: Neo4j 图关系存储

系统 SHALL 支持存储方法节点和调用关系，构建代码图谱。

#### Scenario: 创建方法节点
- **GIVEN** 方法信息（名称、文件路径、类名）
- **WHEN** 调用 add_method_node 方法
- **THEN** 在 Neo4j 中创建 Method 节点

#### Scenario: 创建调用关系
- **GIVEN** 源方法名和目标方法名
- **WHEN** 调用 add_call_relationship 方法
- **THEN** 在 Neo4j 中创建 CALLS 关系

---

### Requirement: 主流水线编排

系统 SHALL 支持将上述模块串联成完整的数据处理流水线。

#### Scenario: 执行完整流水线
- **GIVEN** 配置了目标项目路径和大模型 API
- **WHEN** 执行 main() 函数
- **THEN** 按顺序完成：扫描文件 -> 获取Git历史 -> AST解析 -> 大模型摘要 -> 存储入库

---

## MODIFIED Requirements

### Requirement: 无

本规格文档不涉及对现有功能的修改。

---

## REMOVED Requirements

### Requirement: 无

本规格文档不涉及移除现有功能。

---

## Technical Specifications

### 依赖版本

| 依赖包 | 版本 | 用途 |
|--------|------|------|
| tree-sitter | 0.22.3 | AST 解析 |
| tree-sitter-java | 0.21.0 | Java 语法支持 |
| chromadb | 0.4.24 | 向量数据库 |
| neo4j | 5.20.0 | 图数据库 |
| GitPython | 3.1.43 | Git 历史解析 |
| requests | 2.31.0 | HTTP 请求 |
| tqdm | 4.66.4 | 进度条 |

### 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| PROJECT_PATH | 目标Java项目路径 | D:\workspace\YourJavaProject |
| CHROMA_DB_PATH | 向量库存储路径 | ./chroma_data |
| LLM_API_URL | 大模型API地址 | http://localhost:11434/api/generate |
| LLM_MODEL | 模型名称 | qwen2.5:14b |

### 数据模型

#### ChromaDB Collection: java_code_kb

| 字段 | 类型 | 说明 |
|------|------|------|
| documents | string | 中文摘要文本 |
| metadatas | dict | 元数据（含原始代码） |

#### Metadata 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| file_path | string | 源文件路径 |
| method_name | string | 方法名 |
| author | string | 最后修改作者 |
| commit_msg | string | 提交消息 |
| raw_code | string | 原始代码 |

### Neo4j 图模型

#### 节点: Method
- name: 方法名
- file_path: 文件路径
- class_name: 所属类名

#### 关系: CALLS
- (Method)-[:CALLS]->(Method)

#### 关系: BELONGS_TO
- (Method)-[:BELONGS_TO]->(Class)
