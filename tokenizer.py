from transformers import AutoTokenizer

tokenizer_mapping = {
    "qwq-32b": AutoTokenizer.from_pretrained("/chenyaofo/hf_models/QwQ-32B", trust_remote_code=True),
}

def get_tokenizer(model_name: str) -> AutoTokenizer:
    if model_name in tokenizer_mapping:
        return tokenizer_mapping[model_name]
    else:
        raise ValueError(f"Model name {model_name} not found in tokenizer_mapping")
    