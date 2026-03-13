


太棒了！既然决定全面拥抱 Python 生态，我们将构建一个原生的 **GraphRAG（图检索增强生成）代码知识库工具**。

这是一份为你量身定制的**完整技术文档与开发指南**。它包含了项目架构、环境依赖、核心处理流程，以及一份**可直接运行的核心骨架代码**，让你今晚就能跑通“代码 -> LLM摘要 -> 向量库”的核心链路。

---

# 🚀 项目名称：Code-GraphRAG (智能代码知识库构建工具)

## 一、 项目架构蓝图

本项目将把本地的代码仓库（如 Java 项目）转化为一个包含**语义搜索（VectorDB）**和**调用关系（GraphDB）**的立体知识库。

### 1. 核心流水线 (Pipeline)
1. **Source Scanner (扫描器)**：遍历本地项目目录，按 `.gitignore` 规则过滤文件。
2. **Git Analyzer (历史溯源)**：提取文件的最近修改记录（Commit Hash, Author, Message）。
3. **AST Parser (语法树解析)**：使用 `tree-sitter` 将 Java 源文件精准切分为类（Class）和方法（Method）级别的代码块。
4. **LLM Processor (AI 处理)**：将“原始代码 + Git历史”发给**本地大模型**，生成自然语言摘要和依赖关系。
5. **Storage Engine (双引擎存储)**：
   - **ChromaDB**：存储代码文本、摘要文本及其 Embedding 向量（用于语义问答）。
   - **Neo4j**：存储类、方法及其调用关系（`CALLS`, `BELONGS_TO`），构建代码图谱。

---

## 二、 环境准备与依赖 (Requirements)

请确保你的 Python 版本为 **3.10+**。

### 1. 创建虚拟环境并激活
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
```

### 2. 安装核心依赖 (`requirements.txt`)
将以下内容保存为 `requirements.txt` 并执行 `pip install -r requirements.txt`：

```text
# 语法树解析 (支持最新版的免编译安装)
tree-sitter==0.22.3
tree-sitter-java==0.21.0

# 向量数据库
chromadb==0.4.24

# 图数据库驱动
neo4j==5.20.0

# Git 历史解析
GitPython==3.1.43

# HTTP 请求与进度条 (用于调用本地大模型)
requests==2.31.0
tqdm==4.66.4
```

---

## 三、 核心骨架代码实现

下面是项目的核心 Python 代码 `main.py`。它实现了从**读取文件 -> AST 切分 -> 调用本地大模型 -> 存入 ChromaDB** 的完整闭环。

*(注：为了让你快速跑通，此版本以 ChromaDB 向量库为主线，图数据库 Neo4j 的写入预留了扩展接口)*

```python
import os
import json
import requests
from pathlib import Path
from tqdm import tqdm
from git import Repo
import chromadb
from tree_sitter import Language, Parser
import tree_sitter_java

# ==========================================
# 1. 配置中心 (Config)
# ==========================================
class Config:
    PROJECT_PATH = r"D:\workspace\YourJavaProject"  # 替换为你的目标Java项目路径
    CHROMA_DB_PATH = "./chroma_data"
    
    # 本地大模型接口配置 (假设使用 Ollama/vLLM，兼容 OpenAI 格式)
    LLM_API_URL = "http://localhost:11434/api/generate" # 以 Ollama 为例
    LLM_MODEL = "qwen2.5:14b" # 替换为你的本地模型名
    
    # 向量模型配置 (如果你使用本地独立的 Embeding API，可以在 Chroma 中配置自定义的 Embedding Function，这里默认使用 Chroma 自带的轻量级模型)
    
# ==========================================
# 2. Git 分析器 (Git Analyzer)
# ==========================================
class GitAnalyzer:
    def __init__(self, repo_path):
        try:
            self.repo = Repo(repo_path)
            self.has_git = True
        except Exception:
            self.has_git = False
            print("未检测到有效的 Git 仓库，跳过 Git 历史提取。")

    def get_file_last_commit(self, file_path):
        """获取文件最后一次修改的 Commit 信息"""
        if not self.has_git:
            return {"author": "Unknown", "message": "No Git", "date": "Unknown"}
        
        try:
            # 获取相对路径
            rel_path = os.path.relpath(file_path, self.repo.working_tree_dir)
            # 获取最近一次 commit
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=1))
            if commits:
                c = commits[0]
                return {
                    "author": c.author.name,
                    "message": c.message.strip(),
                    "date": c.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            pass
        return {"author": "Unknown", "message": "Unknown", "date": "Unknown"}

# ==========================================
# 3. AST 代码解析器 (Tree-sitter Parser)
# ==========================================
class JavaParser:
    def __init__(self):
        # 初始化 Java 语法树解析器 (v0.22+ 语法)
        self.JAVA_LANGUAGE = Language(tree_sitter_java.language())
        self.parser = Parser(self.JAVA_LANGUAGE)

    def extract_methods(self, file_path):
        """解析 Java 文件，提取所有方法及其源码块"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
            
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        methods =[]
        # 简单的 AST 遍历寻找方法声明
        def traverse(node):
            if node.type == 'method_declaration':
                # 提取方法名
                name_node = node.child_by_field_name('name')
                method_name = code[name_node.start_byte:name_node.end_byte] if name_node else "unknown_method"
                # 提取方法完整代码
                method_code = code[node.start_byte:node.end_byte]
                methods.append({
                    "name": method_name,
                    "code": method_code
                })
            for child in node.children:
                traverse(child)
                
        traverse(root_node)
        return methods

# ==========================================
# 4. 大模型交互层 (LLM Processor)
# ==========================================
class LLMProcessor:
    @staticmethod
    def generate_summary(method_name, code, git_info):
        """调用本地大模型生成代码摘要"""
        prompt = f"""
        你是一个资深的 Java 架构师。请分析以下 Java 方法代码。
        
        【上下文信息】
        - 方法名：{method_name}
        - 最后修改人：{git_info['author']}
        - 修改原因(Git Log)：{git_info['message']}
        
        【源代码】
        ```java
        {code}
        ```
        
        请用简洁的中文输出：
        1. 该方法的核心业务功能是什么？
        2. 它可能涉及哪些外部调用或依赖？
        （只需输出总结文字，不要超过200字）
        """
        
        payload = {
            "model": Config.LLM_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            # 注意：这里的请求结构适配 Ollama。如果你用 vLLM/OpenAI 格式，请修改 payload 结构
            response = requests.post(Config.LLM_API_URL, json=payload, timeout=30)
            response.raise_for_status()
            return response.json().get("response", "大模型未返回有效内容")
        except Exception as e:
            return f"大模型生成失败: {str(e)}"

# ==========================================
# 5. 向量库管理层 (ChromaDB Vector Store)
# ==========================================
class KnowledgeBase:
    def __init__(self):
        # 实例化本地 Chroma 客户端
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        # 获取或创建集合 (使用 Chroma 内置的文本嵌入模型)
        self.collection = self.client.get_or_create_collection(name="java_code_kb")
        
    def add_code_chunk(self, chunk_id, summary, code, metadata):
        """存入向量数据库"""
        # 我们对“自然语言摘要”进行向量化，原始代码存入 metadata
        metadata["raw_code"] = code
        self.collection.add(
            documents=[summary], # 对中文摘要进行向量化，极大提升检索准确率
            metadatas=[metadata],
            ids=[chunk_id]
        )

# ==========================================
# 6. 主流水线编排 (Main Pipeline)
# ==========================================
def main():
    print("🚀 启动 Code-GraphRAG 构建流水线...")
    
    # 1. 初始化各模块
    git_analyzer = GitAnalyzer(Config.PROJECT_PATH)
    parser = JavaParser()
    kb = KnowledgeBase()
    
    # 2. 扫描 Java 文件
    java_files =[]
    for root, dirs, files in os.walk(Config.PROJECT_PATH):
        if ".git" in root or "target" in root: # 简单过滤
            continue
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
                
    print(f"📂 发现 {len(java_files)} 个 Java 源文件，开始解析...")
    
    # 3. 开始处理流水线
    for file_path in tqdm(java_files, desc="Processing Files"):
        # 3.1 提取文件级 Git 历史
        git_info = git_analyzer.get_file_last_commit(file_path)
        
        # 3.2 AST 解析出方法
        methods = parser.extract_methods(file_path)
        
        for method in methods:
            chunk_id = f"{file_path}_{method['name']}".replace("\\", "_").replace("/", "_")
            
            # 3.3 调用大模型生成摘要
            summary = LLMProcessor.generate_summary(method["name"], method["code"], git_info)
            
            # 3.4 组装 Metadata 并入库
            metadata = {
                "file_path": file_path,
                "method_name": method["name"],
                "author": git_info["author"],
                "commit_msg": git_info["message"]
            }
            kb.add_code_chunk(chunk_id, summary, method["code"], metadata)
            
            # 【扩展锚点】：在这里，你可以提取出跨类的调用关系，调用 Neo4j 的图数据库入库代码
            # neo4j_client.create_method_node(...)
            
    print("\n✅ 知识库构建完成！数据已持久化至:", Config.CHROMA_DB_PATH)

if __name__ == "__main__":
    main()
```

---

## 四、 如何运行与测试？

### 第一步：准备好你的大模型接口
确保你的本地大模型服务正在运行。
*   如果是 **Ollama**：确认 `http://localhost:11434/api/generate` 可用，且已经拉取了模型（如 `ollama run qwen2.5:14b`）。
*   如果是 **其他兼容 OpenAI 的接口**（如 vLLM / LM Studio / 自建 FastAPI）：请修改代码 `LLMProcessor` 中的 `payload` 结构为 `{"messages":[{"role": "user", "content": prompt}]}`。

### 第二步：修改配置并运行
1. 打开 `main.py`。
2. 将 `Config.PROJECT_PATH` 修改为你本地一个真实的 Java 项目（建议先用一个只有几个 Java 文件的极小项目测试）。
3. 运行脚本：
   ```bash
   python main.py
   ```
4. 你会看到炫酷的进度条，它正在逐个解析 Java 文件、请求大模型、并写入本地的 `./chroma_data` 目录。

### 第三步：验证与检索 (Search Test)
构建完成后，你可以新建一个 `scripts/search.py` 脚本来验证成果：

```python
import chromadb

# 连接本地知识库
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_collection(name="java_code_kb")

# 用自然语言向你的代码库提问！
question = "哪里包含了处理支付请求的逻辑？"
results = collection.query(
    query_texts=[question],
    n_results=2 # 返回最相关的两个代码块
)

print(f"🔍 检索结果：\n")
for i in range(len(results['documents'][0])):
    print(f"【匹配摘要】: {results['documents'][0][i]}")
    print(f"【所在文件】: {results['metadatas'][0][i]['file_path']}")
    print(f"【原始代码】:\n{results['metadatas'][0][i]['raw_code'][:200]}...\n")
    print("-" * 50)
```

---

## 五、 后续演进路线 (Roadmap to Neo4j)

当你跑通了上面的核心流程，你会获得一个极其强大的**语义代码搜索引擎**。接下来的进阶动作是引入 **Neo4j** 构建图结构：

1. **安装并启动 Neo4j** (推荐使用 Docker: `docker run -d -p 7474:7474 -p 7687:7687 neo4j`)。
2. **在 AST 阶段加强解析**：在 `JavaParser.extract_methods` 中，不仅提取方法名，同时提取方法体内的**方法调用表达式 (Method Invocation)**。
3. **将关系推入 Neo4j**：在主循环中，增加一步写入：
   ```python
   # 使用 neo4j 驱动执行 Cypher 语句
   cypher = """
   MERGE (m1:Method {name: $source})
   MERGE (m2:Method {name: $target})
   MERGE (m1)-[:CALLS]->(m2)
   """
   ```
4. **混合查询 (GraphRAG)**：在问答时，先用 ChromaDB 查出入口函数，再用 Neo4j 查询该入口函数的上下游链路，一起喂给大模型回答！

祝你构建成功！如果有任何解析报错或大模型对接问题，随时告诉我！