import json
import requests
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from search_database_manager import SearchDatabaseManager


def bocha_web_search(search_query: str, api_key: str, endpoint: str, num_results: int=10):
    """
    Perform a web search using the Bocha API.

    Args:
        search_query (str): The search query.
        bocha_api_key (str): The Bocha API key.
        num_results (int): The number of search results to retrieve.

    Returns:
        list: A list of dictionaries containing the extracted information.
    """
    payload = json.dumps({
        'query': search_query,
        'summary': True,
        'freshness': 'noLimit',  # 支持 noLimit、oneDay、oneWeek、oneMonth、oneYear
        'count': num_results
    })
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    response = requests.post(endpoint, headers=headers, data=payload)
    search_results = response.json()
    return search_results.get('data', {})

def tavily_web_search(search_query: str, api_key: str, endpoint: str, num_results: int=10):
    """
    Perform a web search using the Tavily API.

    Args:
        search_query (str): The search query.
        api_key (str): The Tavily API key.
        num_results (int): The number of search results to retrieve.

    Returns:
        list: A list of dictionaries containing the extracted information.
    """
    payload = {
        "query": search_query,
        "search_depth": 'basic',
        "topic": 'general',
        "days": 3,
        "include_answer": False,
        "include_raw_content": True,
        "max_results": num_results,
        "include_domains": [],
        "exclude_domains": [],
        "include_images": False,
    }
    headers = {
        "Content-Type": "application/json",
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
    return response.json()

def process_search_queries(
        search_queries: List[str], 
        api_key: str, 
        endpoint: str, 
        num_results_per_query: int=10, 
        max_workers: int=32,
        search_db_manager: SearchDatabaseManager=None
    ):
    """
    Process multiple search queries concurrently using multi-threading.

    Args:
        search_queries (list): A list of search queries.
        api_key (str): The Bocha API key.
        endpoint (str): The Bocha API endpoint.
        num_results (int): The number of search results to retrieve.

    Returns:
        dict: A dictionary where the keys are the search queries and the values are the search results.
    """
    results = {}

    query_cached = []
    if search_db_manager:
        for query in search_queries:
            cached_results = search_db_manager.get(query, num_results=num_results_per_query)
            if not cached_results: continue
            results[query] = cached_results
            query_cached.append(query)
    query_filtered = [q for q in search_queries if q not in query_cached]

    # If all queries have cached results, return directly
    if len(query_filtered) == 0: return results

    results_filtered = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(query_filtered))) as executor:
        # Submit tasks to the executor
        future_to_query = {
            executor.submit(
                # tavily_web_search, query, api_key, endpoint, num_results_per_query
                bocha_web_search, query, api_key, endpoint, num_results_per_query
            ): query 
            for query in query_filtered
        }

        # Process the results as they are completed
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                results_filtered[query] = future.result()
            except Exception as e:
                print(f"Error processing query '{query}': {e}")
    
    # Save the results to the database
    if search_db_manager:
        search_db_manager.batch_upsert([
            {
                "original_query": query, 
                "num_results": num_results_per_query, 
                "results": result
            } for query, result in results_filtered.items()
        ])

    results.update(results_filtered)

    return results
