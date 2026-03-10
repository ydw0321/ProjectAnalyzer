import requests
from src.config import Config


class LLMProcessor:
    @staticmethod
    def generate_summary(method_name: str, code: str, git_info: dict) -> str:
        last_author = git_info.get("author", "Unknown")
        commit_message = git_info.get("message", "Unknown")

        prompt = f"""请分析以下Java方法，用简洁的中文（不超过200字）描述其核心业务功能和外部调用/依赖。

上下文信息：
- 方法名：{method_name}
- 最后修改人：{last_author}
- 修改原因：{commit_message}

源代码：
```{code}
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
