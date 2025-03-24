import json
from typing import List, Dict, Generator, Optional
import openai
from openai import NOT_GIVEN
from tokenizer import get_tokenizer


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


class CheckBuffer:
    def __init__(self, truncate_seqs: list[str], model_name: str):
        self.tokenizer = get_tokenizer(model_name)
        self.buffer = []
        self.check_seqs = [self._tokenize(seq) for seq in set(truncate_seqs) if seq]
        self.max_len = max(len(seq) for seq in self.check_seqs) if self.check_seqs else 0
        self.match_record = []
        print(len(self.check_seqs[0]))
        print([[f'"{t}"' for t in seqs] for seqs in self.check_seqs])
        
        assert self.max_len > 0, "Truncate sequences must be non-empty."
        self._init_match_record()
    
    def _init_match_record(self):
        self.match_record[:] = [list() for _ in range(self.max_len)]

    def _tokenize(self, inp: str) -> List[str]:
        return [
            self.tokenizer.convert_tokens_to_string([token]) 
            for token in self.tokenizer.tokenize(inp)
        ]
    
    def check(self, chunk: str) -> Generator[Optional[str|bool|None], None, None]:
        tokens = self._tokenize(chunk)
        for token in tokens:
            yield self._check_token(token)

    def _check_token(self, item: str) -> Optional[str|bool|None]:
        idx = len(self.buffer)
        search_idx = [i for i in range(len(self.check_seqs))] if idx==0 else \
                     self.match_record[idx-1]  # last token's all match sequence id
        
        matched = False
        for index in search_idx:
            if self.check_seqs[index][idx] == item:
                self.match_record[idx].append(index)
                matched = True
        if not matched:
            res = ''.join(self.buffer+[item])
            self._init_match_record()
            self.buffer.clear()
            return res
        else:
            for index in self.match_record[idx]:
                if len(self.check_seqs[index])==len(self.buffer)+1:
                    print('Hit: ', self.check_seqs[index])
                    return True
            else:
                self.buffer.append(item)
                return None


def llm_response_iter_stream(
    messages: List[Dict] = [],
    model: str = '',
    key: str = '',
    api_url: str = '',
    num_res: int = 1,
    truncate_seqs: list[str] = [],
) -> Generator[str, None, None]:
    
    assert num_res == 1, "num_res must be 1 in interactive mode."

    client = openai.Client(api_key=key, base_url=api_url)

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        stream=True,
        n=num_res,
    )
    
    buffer = CheckBuffer(truncate_seqs, model)

    for chunk in stream:
        if not chunk.choices or not chunk.choices[0].delta: continue
        delta = chunk.choices[0].delta
        content, reasoning_content = delta.content, delta.reasoning_content
        if not content and not reasoning_content:
            continue
        # only one in content and reasoning_content is not empty
        if bool(content) == bool(reasoning_content):
            print("content and reasoning_content must be exclusive.")
            continue
        # truncate reasoning_content
        if content:
            formatted_chunk = {
                "id": chunk.id,  # 必须包含id
                "object": "chat.completion.chunk",
                "created": chunk.created,
                "model": chunk.model,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "stop": '1', # TODO
                        "content": content,
                        "reasoning_content": '',
                        "role": delta.role  # 保留其他delta字段
                    },
                    "finish_reason": chunk.choices[0].finish_reason
                }]
            }
            yield f"data: {json.dumps(formatted_chunk)}\n\n"
        else:
            match_flag = False
            for res in buffer.check(reasoning_content):
                if res == None: continue
                elif res == True: 
                    match_flag = True
                    break
                else:
                    formatted_chunk = {
                        "id": chunk.id,  # 必须包含id
                        "object": "chat.completion.chunk",
                        "created": chunk.created,
                        "model": chunk.model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "stop": '0', # TODO
                                "content": '',
                                "reasoning_content": res,
                                "role": delta.role  # 保留其他delta字段
                            },
                            "finish_reason": chunk.choices[0].finish_reason
                        }]
                    }
                    yield f"data: {json.dumps(formatted_chunk)}\n\n"
            if match_flag: break
            print(reasoning_content, end='')
    yield "data: [DONE]\n\n"
