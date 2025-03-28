EXTRACT_ERROR_MAKER = '<|ExtractError|>'
MODEL_INFOS = [
    { "model_name": "qwq-32b", "isThink": True, "label": "数学推理", "order": 1 },
    { "model_name": "qwen2.5-72b-instruct", "isThink": False, "label": "中文顶尖", "order": 2 },
    { "model_name": "deepseek-v3", "isThink": False, "label": "满血版v3，深度推理", "order": 3 },
    { "model_name": "qwen2.5-7b-instruct", "isThink": False, "label": "快速响应", "order": 4 },
    { "model_name": "deepseek-r1-distill-qwen-32b", "isThink": True, "label": "蒸馏版，深度推理", "order": 5 },
    { "model_name": "qwen2.5-32b-instruct", "isThink": False, "label": "性能均衡", "order": 6 },
    { "model_name": "deepseek-r1", "isThink": True, "label": "满血版r1，深度推理", "order": 7 },
    { "model_name": "qwen2.5-coder-32b-instruct", "isThink": False, "label": "代码专家", "order": 8 },
    { "model_name": "llama-3.3-70b-instruct", "isThink": False, "label": "海外开源", "order": 9 },
]
FEACH_HTTP_TIMEOUT = 4
# SEARCH_API_URL = "https://api.tavily.com/search"
SEARCH_API_URL = "https://api.bochaai.com/v1/web-search"
# GPT_MODEL_API = 'https://dashscope.aliyuncs.com/compatible-mode/v1'  # Qwen API
GPT_MODEL_API = 'https://cloud.infini-ai.com/maas/v1'
GPT_MODEL_NAME = 'qwen2.5-72b-instruct'