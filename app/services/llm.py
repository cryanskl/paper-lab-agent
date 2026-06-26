from typing import Any


def chat_completion_content(data: Any) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("chat completion response missing choices[0].message.content") from exc
    if not isinstance(content, str) or not content.strip():
        raise ValueError("chat completion response missing choices[0].message.content")
    return content
