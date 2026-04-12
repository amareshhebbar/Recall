import json
import logging
import litellm
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
# from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.async_configs import BrowserConfig
from crawl4ai import LLMExtractionStrategy, LLMConfig

from blueprints.index import AgenticExtraction

model_chosen = "ollama" 

model_configs = {
    "openai": {"provider": "openai/gpt-4o", "api_key": "your_openai_key"},
    "gemini": {"provider": "gemini/gemini-2.5-flash-lite", "api_key": "your_gemini-key"},
    "claude": {"provider": "anthropic/claude-3-5-sonnet-20240620", "api_key": "your_claude_key"},
    "ollama": {
        "provider": "ollama/llama3.1", 
        "api_base": "http://localhost:11434"
    }
}

selected = model_configs.get(model_chosen, model_configs["openai"])

gpu_queue = asyncio.Semaphore(1)

async def evaluate_agentic_state(raw_html: str, current_url: str, user_prompt: str) -> dict:
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
        provider=selected["provider"], 
        api_token=selected.get("api_key", "dummy_local_key"), 
           
        base_url=selected.get("api_base")
        ),
        schema=AgenticExtraction.model_json_schema(),
        extraction_type="schema",
        instruction=f"You are an autonomous web extraction agent navigating {current_url}. Your primary goal: {user_prompt}. Extract relevant entities strictly matching this criteria. Then, analyze the DOM to determine the best next URLs to navigate to, or buttons to click to find more matching data.",
        chunk_token_threshold=3000, 
        apply_chunking=True,
        overlap_rate=0.1,
        verbose=True
    )

    browser_cfg = BrowserConfig(headless=True)
    
    run_conf = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10 
    )
    async with gpu_queue:
            logging.info(f"[{current_url}] GPU acquired! Extracting data with Ollama...")
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                raw_url = f"raw:{raw_html}"
                result = await crawler.arun(url=raw_url, config=run_conf)
                
                if result.success and result.extracted_content:
                    try:
                        content = result.extracted_content
                        return json.loads(content) if isinstance(content, str) else content
                    except json.JSONDecodeError:
                        logging.error("Ollama returned malformed JSON.")
                        return {}
                else:
                    logging.error(f"Cognitive extraction failed: {result.error_message}")
                    return {}
