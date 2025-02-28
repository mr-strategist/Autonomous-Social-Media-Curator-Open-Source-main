from crewai import LLM
import os

def get_llm():
    """Get configured LLM using Deepseek API"""
    return LLM(
        provider="deepseek",  # Specify Deepseek as provider
        model="deepseek-chat",  # Use Deepseek chat model
        api_key=os.getenv('DEEPSEEK_API_KEY'),  # Deepseek API key
        base_url="https://api.deepseek.com/v1",  # Deepseek API endpoint
        temperature=0.7,
        max_tokens=1500,
        config={
            "request_timeout": 120,
            "model_kwargs": {
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "stop": None
            }
        }
    )