import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict

from template import KEYWORD_EXTRACT_HH_MK_TEMPLATE_ZH, KEYWORD_EXTRACT_NH_MK_TEMPLATE_ZH, SKIP_SEARCH_MAKER
from const import EXTRACT_ERROR_MAKER, MODEL_INFOS, GPT_MODEL_NAME, SEARCH_API_URL, GPT_MODEL_API
from private_key import GPT_MODEL_KEY, SEARCH_API_KEY, JINA_API_KEY
from crawler_database_manager import CrawlerDatabaseManager
from search_database_manager import SearchDatabaseManager
from search import process_search_queries
from fetch import fetch_page_content, extract_snippet_with_context
from LLM import llm_response_stream, llm_response
from utils import extract_relevant_info, \
                  deduplicate_relevant_info_list, \
                  rerank_info_id, \
                  history_to_str, \
                  remove_id, \
                  extract_keywords


app = FastAPI()

# 外部 API 的 URL 和认证信息
USE_JINA_API = False
max_keyword_num = 4
search_num = 10
top_k = 2
max_doc_len = 3000
cache_db_manager = CrawlerDatabaseManager('crawler_data.db')
search_cache_db_manager = SearchDatabaseManager('search_data.db', outdated_days=0)

class QuestionRequest(BaseModel):
    question: str
    history: List[Dict]

class SearchRequest(BaseModel):
    keywords: List[str]

class AnswerRequest(BaseModel):
    question: str
    history: List[Dict]
    search_context: List[Dict]
    model_name: str

class OpenaiRequest(BaseModel):
    model: str
    messages: List[Dict]
    temperature: float = 0.0
    stream: bool = True
    search_context_url: List[str] = []

@app.post("/gen_keywords")
async def get_keywords(request: QuestionRequest):
    query = request.question.strip()
    history = request.history

    if not query:
        return {"keywords": []}

    search_queries = llm_response(
        KEYWORD_EXTRACT_HH_MK_TEMPLATE_ZH.format(
            chat_history=history_to_str(history), question=query
        ) if history else KEYWORD_EXTRACT_NH_MK_TEMPLATE_ZH.format(question=query), 
        model=GPT_MODEL_NAME,
        key=GPT_MODEL_KEY,
        api_url=GPT_MODEL_API,
    )
    if search_queries == SKIP_SEARCH_MAKER:
        print(f"Skip search：{query}")
        return {"keywords": []}
    else:
        search_queries = extract_keywords(search_queries)[:max_keyword_num]
        for keyword in search_queries:
            if len(keyword) > 20:
                search_queries.remove(keyword)
        print(search_queries)
        return {"keywords": search_queries}

@app.post("/search")
async def search(request: SearchRequest):
    search_queries = request.keywords
    if not search_queries:
        return {"search_results": []}

    query_to_search_results = process_search_queries(
        search_queries, SEARCH_API_KEY, SEARCH_API_URL, 
        num_results_per_query=search_num,
        search_db_manager=search_cache_db_manager
    )
    relevant_info = deduplicate_relevant_info_list(
        [
            extract_relevant_info(results)[:top_k]
            for results in query_to_search_results.values()
        ]
    )
    urls_to_fetch = [it['url'] for it in relevant_info if not it['context']]  # not include the context
    urls_to_fetch_filtered = [u for u in urls_to_fetch if cache_db_manager.get(u) is None]  # not include the cache
    cached_urls = [u for u in urls_to_fetch if u not in urls_to_fetch_filtered]

    if urls_to_fetch_filtered:
        try:
            fetched_contents = fetch_page_content(
                urls_to_fetch_filtered,
                use_jina=USE_JINA_API,
                jina_api_key=JINA_API_KEY,
            )
            print(f"Fetched {len(fetched_contents)} URLs successfully.")
        except Exception as e:
            print(f"Error during batch URL fetching: {e}")
            fetched_contents = {url: f"Error fetching URL: {e}" for url in urls_to_fetch_filtered}

    for i, doc_info in enumerate(relevant_info):
        url = doc_info['url']
        if url in cached_urls:
            raw_context = cache_db_manager.get(url)['context']
        elif url in urls_to_fetch_filtered:
            raw_context = fetched_contents.get(url, "")
        else:
            raw_context = doc_info['context']
        doc_info['snippet'] = doc_info['snippet'].replace('<b>','').replace('</b>','')
        success, filtered_context = extract_snippet_with_context(raw_context, doc_info['snippet'], context_chars=max_doc_len)
        if success:
            context = filtered_context
        else:
            context = raw_context[:max_doc_len*2]

        doc_info['context'] = context
    
    # post-process the relevant info
    print(f'before post-process num is {len(relevant_info)}')
    relevant_info = [
        info for info in relevant_info 
        if info['context'].strip() != "" and 
            not info['context'].startswith(EXTRACT_ERROR_MAKER)
    ]
    #TODO 
    cache_db_manager.batch_upsert(remove_id(relevant_info))
    print(f'after post-process num is {len(relevant_info)}')
    return {"search_results": rerank_info_id(relevant_info)}

@app.post("/v1/chat/completions", response_class=StreamingResponse)
async def chat(request: OpenaiRequest):

    print(request.search_context_url)

    search_context = []
    for url in request.search_context_url:
        item = cache_db_manager.get(url)
        if item:
            search_context.append(item)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"URL {url} not found in cache"
            )

    formatted_documents = ""
    for i, info in enumerate(search_context):
        formatted_documents += f"**文档 {i + 1}:**\n"
        formatted_documents += f"**标题：** {info.get('title', '')}\n"
        formatted_documents += f"**URL：** {info.get('url', 'None')}\n"
        formatted_documents += f"**内容：** {info.get('context', '<|Invalid Content|>')}\n\n"

    if formatted_documents:
        messages = request.messages
        question = messages.pop()['content'] + '\n\n下面是一些辅助你回答用户问题的参考资料，请你以`[序号]`对生成中参考了资料的部分标注对应的资料序号：\n\n' + formatted_documents
        # print(question)
        messages.append({'role': 'user', 'content': question})
    else:
        messages = request.messages

    try:
        response = llm_response_stream(
            messages=messages,
            model=request.model,
            key=GPT_MODEL_KEY,
            api_url=GPT_MODEL_API,
        )
        return StreamingResponse(
            content=response,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stream generation failed: {str(e)}"
        )

@app.get("/models")
async def get_models():
    return {"models": MODEL_INFOS}

if __name__ == "__main__":
    # uvicorn.run('web_search:app', host="0.0.0.0", port=8000, reload=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)