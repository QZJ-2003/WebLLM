import re
import time
import string
import requests
from io import BytesIO
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import pdfplumber
from bs4 import BeautifulSoup
from tqdm import tqdm

import nltk
nltk_path = '/chenyaofo/datasets/nltk_data'
nltk.data.path.append(nltk_path)
# nltk.download('punkt', download_dir=nltk_path)
from nltk.tokenize import sent_tokenize

from const import EXTRACT_ERROR_MAKER, FEACH_HTTP_TIMEOUT
from utils import detect_language_ratio

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/58.0.3029.110 Safari/537.36',
    'Referer': 'https://www.google.com/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
session = requests.Session()
session.headers.update(headers)


def remove_punctuation(text: str) -> str:
    """Remove punctuation from the text."""
    return text.translate(str.maketrans("", "", string.punctuation))

def remove_punctuation_chinese(text: str) -> str:
    """Remove Chinese punctuation from the text."""
    # 定义中文标点符号
    chinese_punctuation = "。，、；：？！“”‘’（）《》【】{}～—　"  # 可以根据需要扩展
    # 创建翻译表，将标点符号映射为 None
    translator = str.maketrans("", "", chinese_punctuation)
    # 去除标点符号
    return text.translate(translator)

def chinese_sent_tokenize(text):
    # 定义中文句子分隔符的正则表达式
    pattern = r'([。！？；;!?])'
    
    # 使用正则表达式进行分句
    sentences = re.split(pattern, text)

    # 将分隔符与句子重新组合
    sentences = [sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '') 
                 for i in range(0, len(sentences)-1, 2)]
    
    # 去除空白句子
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

def f1_score(true_set: set, pred_set: set) -> float:
    """Calculate the F1 score between two sets of words."""
    intersection = len(true_set.intersection(pred_set))
    if not intersection:
        return 0.0
    precision = intersection / float(len(pred_set))
    recall = intersection / float(len(true_set))
    return 2 * (precision * recall) / (precision + recall)

def extract_snippet_with_context(full_text: str, snippet: str, context_chars: int = 2500) -> Tuple[bool, str]:
    """
    Extract the sentence that best matches the snippet and its context from the full text.

    Args:
        full_text (str): The full text extracted from the webpage.
        snippet (str): The snippet to match.
        context_chars (int): Number of characters to include before and after the snippet.

    Returns:
        Tuple[bool, str]: The first element indicates whether extraction was successful, the second element is the extracted context.
    """
    try:
        full_text = full_text[:50000]

        # 检测文本语言比例
        chinese_ratio = detect_language_ratio(full_text)
        
        # 根据语言比例选择处理方法
        if chinese_ratio > 0.5:  # 中文为主
            remove_punct = remove_punctuation_chinese
            tokenize_fn = chinese_sent_tokenize
        else:  # 英文为主
            remove_punct = remove_punctuation
            tokenize_fn = sent_tokenize

        snippet = snippet.lower()
        snippet = remove_punct(snippet)
        snippet_words = set(snippet.split())

        best_sentence = None
        best_f1 = 0.2

        # sentences = re.split(r'(?<=[.!?]) +', full_text)  # Split sentences using regex, supporting ., !, ? endings
        sentences = tokenize_fn(full_text)  # Split sentences using nltk's sent_tokenize

        # print('*'*30)
        # print(len(sentences))
        for sentence in sentences:
            key_sentence = sentence.lower()
            key_sentence = remove_punct(key_sentence)
            sentence_words = set(key_sentence.split())
            f1 = f1_score(snippet_words, sentence_words)
            if f1 > best_f1:
                best_f1 = f1
                best_sentence = sentence

        if best_sentence:
            para_start = full_text.find(best_sentence)
            para_end = para_start + len(best_sentence)
            start_index = max(0, para_start - context_chars)
            end_index = min(len(full_text), para_end + context_chars)
            context = full_text[start_index:end_index]
            return True, context
        else:
            # If no matching sentence is found, return the first context_chars*2 characters of the full text
            return False, full_text[:context_chars * 2]
    except Exception as e:
        return False, f"Failed to extract snippet context due to {str(e)}"

def extract_pdf_text(url):
    """
    Extract text from a PDF.

    Args:
        url (str): URL of the PDF file.

    Returns:
        str: Extracted text content or error message.
    """
    try:
        response = session.get(url, timeout=FEACH_HTTP_TIMEOUT)  # Set timeout to 20 seconds
        if response.status_code != 200:
            return f"{EXTRACT_ERROR_MAKER}Error: Unable to retrieve the PDF (status code {response.status_code})"
        
        # Open the PDF file using pdfplumber
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text
        
        # Limit the text length
        cleaned_text = ' '.join(full_text.split()[:600])
        return cleaned_text
    except requests.exceptions.Timeout:
        return f"{EXTRACT_ERROR_MAKER}Error: Request timed out after 20 seconds"
    except Exception as e:
        return f"{EXTRACT_ERROR_MAKER}Error: {str(e)}"

def extract_text_from_url(url, use_jina=False, jina_api_key=None, snippet: Optional[str] = None):
    """
    Extract text from a URL. If a snippet is provided, extract the context related to it.

    Args:
        url (str): URL of a webpage or PDF.
        use_jina (bool): Whether to use Jina for extraction.
        snippet (Optional[str]): The snippet to search for.

    Returns:
        str: Extracted text or context.
    """
    try:
        if use_jina:
            jina_headers = {
                'Authorization': f'Bearer {jina_api_key}',
                'X-Return-Format': 'markdown',
                # 'X-With-Links-Summary': 'true'
            }
            response = requests.get(f'https://r.jina.ai/{url}', headers=jina_headers).text
            # Remove URLs
            pattern = r"\(https?:.*?\)|\[https?:.*?\]"
            text = re.sub(pattern, "", response).replace('---','-').replace('===','=').replace('   ',' ').replace('   ',' ')
        else:
            response = session.get(url, timeout=FEACH_HTTP_TIMEOUT)  # Set timeout 
            response.raise_for_status()  # Raise HTTPError if the request failed
            # Determine the content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type:
                # If it's a PDF file, extract PDF text
                return extract_pdf_text(url)
            # Try using lxml parser, fallback to html.parser if unavailable
            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except Exception:
                print("lxml parser not found or failed, falling back to html.parser")
                soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)

        if snippet:
            success, context = extract_snippet_with_context(text, snippet)
            if success:
                return context
            else:
                return text
        else:
            # If no snippet is provided, return directly
            return text[:8000]
    except requests.exceptions.HTTPError as http_err:
        return f"{EXTRACT_ERROR_MAKER}HTTP error occurred: {http_err}"
    except requests.exceptions.ConnectionError:
        return f"{EXTRACT_ERROR_MAKER}Error: Connection error occurred"
    except requests.exceptions.Timeout:
        return f"{EXTRACT_ERROR_MAKER}Error: Request timed out after {FEACH_HTTP_TIMEOUT} seconds"
    except Exception as e:
        return f"{EXTRACT_ERROR_MAKER}Unexpected error: {str(e)}"

def fetch_page_content(urls, max_workers=32, use_jina=False, jina_api_key=None, snippets: Optional[dict] = None):
    """
    Concurrently fetch content from multiple URLs.

    Args:
        urls (list): List of URLs to scrape.
        max_workers (int): Maximum number of concurrent threads.
        use_jina (bool): Whether to use Jina for extraction.
        snippets (Optional[dict]): A dictionary mapping URLs to their respective snippets.

    Returns:
        dict: A dictionary mapping URLs to the extracted content or context.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(urls)+1)) as executor:
        # Use tqdm to display a progress bar
        futures = {
            executor.submit(extract_text_from_url, url, use_jina, jina_api_key, snippets.get(url) if snippets else None): url
            for url in urls
        }
        for future in tqdm(as_completed(futures), desc="Fetching URLs", total=len(urls)):
            url = futures[future]
            try:
                data = future.result()
                results[url] = data
            except Exception as exc:
                results[url] = f"Error fetching {url}: {exc}"
            time.sleep(0.2)  # Simple rate limiting TODO
    return results