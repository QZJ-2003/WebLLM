import json
from typing import List, Dict, Generator
import openai


def llm_response(query: str, hisotry: List[Dict]=[], model: str='', key: str='', api_url: str='') -> str:
    client = openai.Client(
        api_key=key,
        base_url=api_url,
    )
    messages = hisotry + [{"role": "user", "content": query}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        stream=False,
    )
    return response.choices[0].message.content

def llm_response_stream_v2(
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
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

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
        # 构造符合OpenAI规范的完整响应块
        formatted_chunk = {
            "id": chunk.id,  # 必须包含id
            "object": "chat.completion.chunk",
            "created": chunk.created,
            "model": chunk.model,
            "choices": [{
                "index": choice.index,
                "delta": {
                    "content": choice.delta.content,
                    "role": choice.delta.role  # 保留其他delta字段
                },
                "finish_reason": choice.finish_reason
            } for choice in chunk.choices]
        }
        if not formatted_chunk['choices'][0]['delta']['content']:
            continue
        
        # 转换为SSE格式
        yield f"data: {json.dumps(formatted_chunk)}\n\n"  # ✅ 关键修改
    
    # 添加流结束标记
    yield "data: [DONE]\n\n"
