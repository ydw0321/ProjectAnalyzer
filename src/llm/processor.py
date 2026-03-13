import requests
from src.config import Config
from typing import List, Optional


class LLMProcessor:
    @staticmethod
    def generate_summary(
        method_name: str,
        code: str,
        git_info: dict,
        class_name: str = "",
        layer: str = "",
        field_deps: Optional[List[str]] = None,
    ) -> str:
        last_author = git_info.get("author", "Unknown")
        commit_message = git_info.get("message", "Unknown")

        layer_hint = f"- 所属层级：{layer}" if layer else ""
        class_hint = f"- 所属类：{class_name}" if class_name else ""
        deps_hint = (
            f"- 字段依赖：{', '.join(field_deps)}"
            if field_deps
            else ""
        )

        prompt = f"""你是一个资深 Java 架构师，正在为一个几十万行的历史老项目建立知识库。
请分析以下 Java 方法，用简洁的中文（不超过 200 字）描述其核心业务功能。

## 上下文信息
- 方法名：{method_name}
{class_hint}
{layer_hint}
{deps_hint}
- 最后修改人：{last_author}
- 修改原因：{commit_message}

## 输出要求
1. **业务职责**：用一句话说清楚这个方法做什么业务
2. **关键依赖**：调用了哪些外部服务/DAO/RPC（可从代码推断）
3. **副作用**：是否写 DB、发消息、调第三方（如有）

## 源代码
```java
{code}
```"""

        try:
            headers = {
                "Authorization": f"Bearer {Config.LLM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": Config.LLM_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
            response = requests.post(
                Config.LLM_API_URL,
                headers=headers,
                json=payload,
                timeout=Config.LLM_TIMEOUT
            )
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            return result.get("content", "大模型未返回有效内容")
        except Exception as e:
            return f"大模型生成失败: {str(e)}"
