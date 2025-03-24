import json
from typing import List, Dict, Generator
import openai
from openai import NOT_GIVEN


def llm_response(query: str, hisotry: List[Dict]=[], model: str='', key: str='', api_url: str='', stop: List[str]=NOT_GIVEN) -> str:
    client = openai.Client(
        api_key=key,
        base_url=api_url,
    )
    messages = hisotry + [{"role": "user", "content": query}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        stop=stop,
        stream=False,
    )
    return response.choices[0].message.content


def llm_response_stream(
    messages: List[Dict] = [],
    model: str = '',
    key: str = '',
    api_url: str = ''
) -> Generator[str, None, None]:
    client = openai.Client(
        api_key=key,
        base_url=api_url,
    )
    
    # 注意：stream=True 已启用流式模式
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        stream=True,
    )
    
    for chunk in stream:
        if not chunk.choices or not chunk.choices[0].delta: continue
        delta = chunk.choices[0].delta
        content = delta.content
        reasoning_content = delta.reasoning_content if hasattr(delta, 'reasoning_content') else ''
        if not content and not reasoning_content: continue
        if bool(content) and bool(reasoning_content):
            print(f"[Error] content: {content}\nreasoning_content: {reasoning_content}")
            continue
        # 构造符合OpenAI规范的完整响应块
        formatted_chunk = {
            "id": chunk.id,  # 必须包含id
            "object": "chat.completion.chunk",
            "created": chunk.created,
            "model": chunk.model,
            "choices": [{  # TODO Only One Choice is returned
                "index": 0,
                "delta": {
                    "content": content,
                    "reasoning_content": reasoning_content,
                    "role": delta.role,
                },
                "finish_reason": chunk.choices[0].finish_reason
            }]
        }        
        yield f"data: {json.dumps(formatted_chunk)}\n\n"  # 转换为SSE格式
        print(content if not reasoning_content else reasoning_content, end='')
    yield "data: [DONE]\n\n"  # 添加流结束标记
