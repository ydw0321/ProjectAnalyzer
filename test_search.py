import chromadb
from src.config import Config

client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
collection = client.get_collection(name="java_code_kb")

question = "处理支付请求的逻辑"
results = collection.query(
    query_texts=[question],
    n_results=3
)

print(f"🔍 检索结果：\n")
for i in range(len(results['documents'][0])):
    print(f"【匹配摘要】: {results['documents'][0][i]}")
    print(f"【所在文件】: {results['metadatas'][0][i]['file_path']}")
    print(f"【方法名】: {results['metadatas'][0][i]['method_name']}")
    print(f"【调用次数】: {results['metadatas'][0][i].get('call_count', 'N/A')}")
    code = results['metadatas'][0][i]['raw_code'][:300] if 'raw_code' in results['metadatas'][0][i] else 'N/A'
    print(f"【原始代码】: {code}...\n")
    print("-" * 50)
