import chromadb
from src.config import Config


def search_knowledge_base(query, top_k=2):
    client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
    collection = client.get_collection(name="java_code_kb")
    results = collection.query(query_texts=[query], n_results=top_k)
    return results


def main():
    print("🔍 语义代码检索")
    default_question = "哪里包含了处理支付请求的逻辑？"
    query = input(f"请输入查询语句（直接回车使用默认问题）: ") or default_question

    results = search_knowledge_base(query, top_k=2)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for i in range(len(documents)):
        print(f"【匹配摘要】: {documents[i]}")
        print(f"【所在文件】: {metadatas[i]['file_path']}")
        print(f"【原始代码】: {metadatas[i]['raw_code'][:200]}...")
        print("-" * 50)


if __name__ == "__main__":
    main()
