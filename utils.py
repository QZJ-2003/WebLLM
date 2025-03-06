import re
from copy import deepcopy
from typing import List, Dict


def extract_relevant_info(search_results: Dict) -> List[Dict]:
    """
    Extract relevant information from Bing search results.

    Args:
        search_results (dict): JSON response from the Bing Web Search API.

    Returns:
        list: A list of dictionaries containing the extracted information.
    """
    useful_info = []
    
    if 'webPages' in search_results and 'value' in search_results['webPages']:
        for id, result in enumerate(search_results['webPages']['value']):
            info = {
                'id': id + 1,  # Increment id for easier subsequent operations
                'keywords': [search_results.get('queryContext', {}).get('originalQuery', '')], # TODO 兼容bing等API嘛？
                'title': result.get('name', ''),
                'url': result.get('url', ''),
                'site_name': result.get('siteName', ''),
                'site_icon': result.get('siteIcon', ''),
                'date': result.get('dateLastCrawled', '').split('T')[0],  # TODO 兼容bing等API嘛？
                'snippet': result.get('snippet', ''),  # Remove HTML tags
                # Add context content to the information
                'context': ''  # Reserved field to be filled later
            }
            useful_info.append(info)
    
    return useful_info

def deduplicate_relevant_info_list(relevant_info_list: List[List[Dict]]):
    """
    Deduplicate a list of relevant information dictionaries based on the URL field.

    Args:
        relevant_info_list (list): A list of dictionaries containing relevant information.

    Returns:
        list: A deduplicated list of dictionaries.
    """
    seen_urls = set()
    deduplicated_dict = {}
    for relevant_info in relevant_info_list:
        for info in relevant_info:
            url = info.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                deduplicated_dict[url] = info
            else:
                deduplicated_dict[url]['keywords'].extend(info['keywords'])
                deduplicated_dict[url]['keywords'] = list(set(deduplicated_dict[url]['keywords']))
    return rerank_info_id(list(deduplicated_dict.values()))

def rerank_info_id(relevant_info):
    """
    Re-rank the ID field in the relevant information list.

    Args:
        relevant_info (list): A list of dictionaries containing relevant information.

    Returns:
        list: A list of dictionaries with re-ranked IDs.
    """
    for index, info in enumerate(relevant_info):
        info['id'] = index + 1
    return relevant_info

def remove_id(relevant_info: List[Dict]) -> List[Dict]:
    """Remove the 'id' field from the relevant info list."""
    return [{k: v for k, v in info.items() if k != 'id'} for info in deepcopy(relevant_info)]

def set_context_empty(relevant_info: List[Dict]) -> List[Dict]:
    """Set the 'context' field to an empty string in the relevant info list."""
    return [{**info, 'context': ''} for info in deepcopy(relevant_info)]

def history_to_str(history, length: int=-1):
    """将对话历史转换为字符串"""
    length = length if length > 0 else len(history)
    context = []
    for turn in history:
        # 只保留用户和助手的最新3轮对话
        if len(context) >= length:  # 3轮对话，每轮2条
            break
        context.append(f"{turn['role']}: {turn['content']}")
    return "\n".join(context)

def extract_keywords(model_output):
    """
    从模型输出中提取关键词，并将关键词中的标点符号替换为空格
    :param model_output: 模型生成的字符串，格式为"keyword1 | keyword2 | keyword3"
    :return: 提取的关键词列表
    """
    if not model_output:
        return []
    
    # 按竖线分割关键词
    keywords = [kw.strip() for kw in model_output.split("|")]
    
    # 去除空字符串
    keywords = [kw for kw in keywords if kw]
    
    # 将每个关键词中的标点符号替换为空格
    keywords = [re.sub(r'[^\w\s]', ' ', kw, flags=re.UNICODE) for kw in keywords]
    # keywords = [re.sub(r'[^\w\s]', ' ', kw, flags=re.ASCII) for kw in keywords]
    
    # 去除多余的空格（将连续多个空格替换为单个空格）
    keywords = [re.sub(r'\s+', ' ', kw).strip() for kw in keywords]
    
    keywords = [keyword for keyword in keywords if keyword]
    return keywords