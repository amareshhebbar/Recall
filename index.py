import asyncio
import logging
import pandas as pd
import json
from typing import List
from pydantic import BaseModel, Field
import traceback
import math
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter  
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator 
from crawl4ai import LLMConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import os
import re
from duckduckgo_search import DDGS
import chromadb
from chromadb.utils import embedding_functions
import ollama

import json
import operator
from typing import Annotated, List, TypedDict, Union

from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage
import sys
from pymilvus import MilvusClient, DataType

import os 
from dotenv import load_dotenv
load_dotenv(); print('\n--- Loaded ENV ---')


ZILLIZ_CLUSTER_ENDPOINT = os.getenv("ZILLIZ_CLUSTER_ENDPOINT")
ZILLIZ_TOKEN = os.getenv("ZILLIZ_TOKEN")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ai_tools_cloud") 

print('ENDPOINT:', ZILLIZ_CLUSTER_ENDPOINT)
print('TOKEN:', ZILLIZ_TOKEN)
print('------------------\n')

DATA_FOLDER = "research_data"
RAW_PARTS_DIR = os.path.join(DATA_FOLDER, "raw_parts") 
CHECKPOINT_FILE = "processed_tools.txt"
FINAL_DATA_FILE = "enriched_tools.jsonl"
RESEARCH_LIMIT = 40 
LINES_PER_PART = 1000 

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(RAW_PARTS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

default_ef = embedding_functions.DefaultEmbeddingFunction()
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="ai_tools", embedding_function=default_ef)

class AgentState(TypedDict):
    name: str
    original_desc: str
    search_results: str
    enriched_data: dict
    source_part: str
    retry_count: int

llm = ChatOllama(model="llama3.1:8b", format="json", temperature=0)
search_tool = DuckDuckGoSearchRun()
logging.getLogger("duckduckgo_search").setLevel(logging.CRITICAL)

def save_final_jsonl(tool_data):
    with open(os.path.join(DATA_FOLDER, FINAL_DATA_FILE), "a", encoding="utf-8") as f:
        f.write(json.dumps(tool_data) + "\n")

def save_checkpoint(tool_name):
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(tool_name + "\n")

def get_processed_tools():
    if not os.path.exists(CHECKPOINT_FILE): return set()
    with open(CHECKPOINT_FILE, "r") as f:
        return set(line.strip() for line in f)

default_ef = embedding_functions.DefaultEmbeddingFunction()

def init_zilliz_collection():
    """Ensures the Zilliz collection exists and has the right schema."""
    z_client = MilvusClient(uri=ZILLIZ_CLUSTER_ENDPOINT, token=ZILLIZ_TOKEN)
    
    if not z_client.has_collection(COLLECTION_NAME="ai_tools"):
        logger.info(f"Creating Zilliz Collection: {COLLECTION_NAME}")

        z_client.create_collection(
            collection_name=COLLECTION_NAME,
            dimension=384, 
            id_type="string",
            max_length=512    
        )
    return z_client


import os
import random
import requests
from tavily import TavilyClient
from langchain_google_genai import ChatGoogleGenerativeAI
from duckduckgo_search import DDGS

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

gemini_search = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite", 
    google_api_key=GOOGLE_API_KEY,
) if GOOGLE_API_KEY else None

async def web_search_node(state: AgentState):
    query = f"{state['name']} AI tool official website pricing documentation"
    logger.info(f"🌐 Search Node: Querying '{query}'")
    
    if gemini_search:
        try:
            res = await gemini_search.ainvoke(f"Search for the official website and pricing of {state['name']}")
            if res.content:
                logger.info(f"✅ Layer 1 (Gemini Grounding) Succeeded")
                return {"search_results": res.content}
        except Exception as e:
            logger.warning(f"⚠️ Layer 1 (Gemini) Failed: {e}")

    if SERPER_API_KEY:
        try:
            url = "https://google.serper.dev/search"
            payload = {"q": query, "num": 3}
            headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            data = response.json()
            results = "\n".join([f"{item['title']}: {item['link']}" for item in data.get('organic', [])])
            if results:
                logger.info(f"✅ Layer 2 (Serper) Succeeded")
                return {"search_results": results}
        except Exception as e:
            logger.warning(f"⚠️ Layer 2 (Serper) Failed: {e}")

    if tavily:
        try:
            tav_res = tavily.search(query=query, max_results=3)
            results = "\n".join([f"{r['title']}: {r['url']}" for r in tav_res['results']])
            logger.info(f"✅ Layer 3 (Tavily) Succeeded")
            return {"search_results": results}
        except Exception as e:
            logger.warning(f"⚠️ Layer 3 (Tavily) Failed: {e}")

    if BRAVE_API_KEY:
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
            params = {"q": query, "count": 3}
            response = requests.get(url, headers=headers, params=params, timeout=5)
            data = response.json()
            results = "\n".join([f"{r['title']}: {r['url']}" for r in data.get('web', {}).get('results', [])])
            if results:
                logger.info(f"✅ Layer 4 (Brave) Succeeded")
                return {"search_results": results}
        except Exception as e:
            logger.warning(f"⚠️ Layer 4 (Brave) Failed: {e}")

    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=3))
            if search_results:
                results = "\n".join([f"{r['title']}: {r['href']}" for r in search_results])
                logger.info(f"✅ Final Fallback (DDG) Succeeded")
                return {"search_results": results}
    except Exception:
        pass

    logger.error(f"❌ All search layers failed for {state['name']}.")
    return {"search_results": f"Online search failed. Use description: {state['original_desc']}"}

async def enrichment_node(state: AgentState):
    """Node: Use Ollama to synthesize the final JSON."""
    logger.info(f"🧠 Enrichment Node: Processing {state['name']}")
    
    prompt = f"""
    You are an expert tech researcher. 
    Tool Name: {state['name']}
    Original Data: {state['original_desc']}
    Web Research: {state['search_results']}

    Provide a JSON object with:
    - name
    - website: (official URL)
    - documentation: (link to docs)
    - pricing_model: (Free, Freemium, Paid, open source or Subscription)
    - multiline_description: (4-12 sentences or 3-4 paragraph)
    - single_line_description: (1 short sentence)
    - pros: [list of 3 pros]
    - cons: [list of 3 cons]
    - icon_url: (best guess URL or leave empty)
    """
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    content = json.loads(response.content)
    return {"enriched_data": content}


workflow = StateGraph(AgentState)

workflow.add_node("search", web_search_node)
workflow.add_node("enrich", enrichment_node)

workflow.set_entry_point("search")
workflow.add_edge("search", "enrich")
workflow.add_edge("enrich", END)

research_agent = workflow.compile()

async def producer(queue: asyncio.Queue, url: str):
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=5.0)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        logger.info(f"🚀 Producer: Crawling {url}")
        result = await crawler.arun(url=url, config=run_config)
        
        if result.success:
            markdown = result.markdown
            lines = markdown.splitlines()
            total_lines = len(lines)
            
            num_parts = math.ceil(total_lines / LINES_PER_PART)
            logger.info(f"分 Splitting {total_lines} lines into {num_parts} parts...")
            
            for i in range(num_parts):
                part_name = f"part_{i+1}.txt"
                start = i * LINES_PER_PART
                end = start + LINES_PER_PART
                part_content = "\n".join(lines[start:end])
                
                with open(os.path.join(RAW_PARTS_DIR, part_name), "w", encoding="utf-8") as f:
                    f.write(part_content)
                
                tool_pattern = r'\d+\.\s*!\[.*?\]\(.*?\)\s*\[\s*(.*?)\s*\]\(.*?\s*"(.*?)"\)'
                found_tools = re.findall(tool_pattern, part_content)
                
                for name, desc in found_tools:
                    await queue.put((name, desc, part_name))
                    
            logger.info("📦 Producer: All parts saved and tools queued.")
        else:
            logger.error(f"Producer Failed: {result.error_message}")
    
    await queue.put(None)


RESEARCH_LIMIT = 40
async def consumer(queue: asyncio.Queue):
    processed = get_processed_tools()
    research_count = 0
    logger.info(f"🤖 Consumer: Starting. Limit set to {RESEARCH_LIMIT} research tasks.")
    while research_count < RESEARCH_LIMIT:
        item = await queue.get()
        if item is None: 
            logger.info("🏁 Producer finished before limit was reached.")
            break
        name, desc, part_name = item
        if name in processed:
            logger.info(f"⏩ Skipping {name} (Already in logs)")
            queue.task_done()
            await asyncio.sleep(random.uniform(7, 15))
            continue
        try:
            logger.info(f"🚀 Invoking LangGraph for: {name}")
            logger.info(f"🚀 [{research_count + 1}/{RESEARCH_LIMIT}] Invoking LangGraph for: {name}")
            initial_state = {"name": name, "original_desc": desc, "source_part": part_name, "search_results": "", "enriched_data": {}, "retry_count": 0}
            final_state = await research_agent.ainvoke(initial_state)
            
            result_data = final_state['enriched_data']
            
            desc_text = result_data.get('multiline_description', '')
            if isinstance(desc_text, list):
                desc_text = " ".join(desc_text)
            
            result_data['multiline_description'] = desc_text
            result_data['name'] = name
            result_data['raw_source_file'] = part_name

            save_final_jsonl(result_data)
            
            save_checkpoint(name)

            collection.add(
                documents=[desc_text], 
                metadatas=[{"name": name, "url": result_data.get('website', '')}],
                ids=[name]
            )
            logger.info(f"✅ Saved directly to ChromaDb Local: {name} ({research_count}/{RESEARCH_LIMIT})")
            logger.info(f"🧠 Generating embedding for {name}")
            vector = default_ef([desc_text])[0]
            
            z_client.insert(
                collection_name=COLLECTION_NAME,
                data=[{
                    "id": name, 
                    "vector": vector, 
                    "text": desc_text, 
                    "url": result_data.get('website', '')
                }]
            )
            research_count += 1
            logger.info(f"✅ Saved directly to Zilliz: {name} ({research_count}/{RESEARCH_LIMIT})")
            
        except Exception as e:
            logger.error(f"❌ Error processing {name}: {e}")
        queue.task_done()
        await asyncio.sleep(random.uniform(7, 15))
    if research_count >= RESEARCH_LIMIT:
        logger.info(f"🛑 Research limit of {RESEARCH_LIMIT} reached. Stopping consumer.")
        while not queue.empty():
            queue.get_nowait()
            queue.task_done()
            await asyncio.sleep(random.uniform(7, 15))


async def validate_environment_and_keys():
    logger.info("==== 🔍 RUNNING PRE-FLIGHT API VALIDATION ====")
    
    if ZILLIZ_CLUSTER_ENDPOINT and ZILLIZ_TOKEN:
        logger.info("⏳ Checking Zilliz Cloud... (This may take up to 15s if the free cluster is waking up)")
        
        def _test_zilliz():
            test_client = MilvusClient(uri=ZILLIZ_CLUSTER_ENDPOINT, token=ZILLIZ_TOKEN)
            test_client.list_collections(timeout=5.0)

        try:
            await asyncio.wait_for(asyncio.to_thread(_test_zilliz), timeout=15.0)
            logger.info("✅ Zilliz Cloud: Connected successfully.")
        except asyncio.TimeoutError:
            logger.error("❌ Zilliz Cloud: TIMED OUT after 15 seconds. (Check if your VPN/Firewall is blocking the connection, or go to the Zilliz dashboard to ensure the cluster is 'Running' and not suspended).")
        except Exception as e:
            logger.error(f"❌ Zilliz Cloud: Connection failed - {e}")
    else:
        logger.warning("⚠️ Zilliz Cloud: Missing endpoint or token in .env")

    if TAVILY_API_KEY:
        logger.info("⏳ Checking Tavily Search...")
        try:
            t_client = TavilyClient(api_key=TAVILY_API_KEY)
            t_client.search("test", max_results=1)
            logger.info("✅ Tavily Search: API Key is valid.")
        except Exception as e:
            logger.error(f"❌ Tavily Search: Validation failed - {e}")
    else:
        logger.warning("⚠️ Tavily Search: Missing API Key in .env")

    if SERPER_API_KEY:
        logger.info("⏳ Checking Serper Search...")
        try:
            res = requests.post("https://google.serper.dev/search", headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}, json={"q": "test"}, timeout=5)
            if res.status_code == 200:
                logger.info("✅ Serper Search: API Key is valid.")
            else:
                logger.error(f"❌ Serper Search: Failed with status {res.status_code}")
        except Exception as e:
            logger.error(f"❌ Serper Search: Validation failed - {e}")
    else:
        logger.warning("⚠️ Serper Search: Missing API Key in .env")

    if BRAVE_API_KEY:
        logger.info("⏳ Checking Brave Search...")
        try:
            res = requests.get("https://api.search.brave.com/res/v1/web/search", headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}, params={"q": "test"}, timeout=5)
            if res.status_code == 200:
                logger.info("✅ Brave Search: API Key is valid.")
            else:
                logger.error(f"❌ Brave Search: Failed with status {res.status_code}")
        except Exception as e:
            logger.error(f"❌ Brave Search: Validation failed - {e}")
    else:
        logger.warning("⚠️ Brave Search: Missing API Key in .env")

    if GOOGLE_API_KEY:
        logger.info("⏳ Checking Google Gemini...")
        try:
            test_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=GOOGLE_API_KEY)
            await test_gemini.ainvoke("Reply 'ok'.")
            logger.info("✅ Google Gemini: API Key is valid.")
        except Exception as e:
            logger.error(f"❌ Google Gemini: Validation failed - {e}")
    else:
        logger.warning("⚠️ Google Gemini: Missing API Key in .env")

    logger.info("==== 🏁 PRE-FLIGHT VALIDATION COMPLETE ====\n")

def get_zilliz_client():
    return MilvusClient(uri=ZILLIZ_CLUSTER_ENDPOINT, token=ZILLIZ_TOKEN)

async def move_to_zilliz():
    logger.info("☁️ Starting migration: ChromaDB -> Zilliz Cloud")
    
    local_data = collection.get()
    if not local_data['ids']:
        logger.info("ℹ️ Local ChromaDB is empty. Nothing to move.")
        return []

    z_client = get_zilliz_client()
    
    if not z_client.has_collection(COLLECTION_NAME):
        z_client.create_collection(
            collection_name=COLLECTION_NAME,
            dimension=384,
        )

    moved_ids = []
    
    for i in range(len(local_data['ids'])):
        tool_id = local_data['ids'][i]
        vector = local_data['embeddings'][i]
        metadata = local_data['metadatas'][i]
        document = local_data['documents'][i]

        res = z_client.query(
            collection_name=COLLECTION_NAME,
            filter=f'id == "{tool_id}"',
            output_fields=["id"]
        )

        if not res:
            z_client.insert(
                collection_name=COLLECTION_NAME,
                data=[{
                    "id": tool_id, 
                    "vector": vector, 
                    "text": document, 
                    "url": metadata.get('url', '')
                }]
            )
            moved_ids.append(tool_id)
            logger.info(f"✅ Migrated to Cloud: {tool_id}")
        else:
            logger.info(f"⏩ {tool_id} already exists in Zilliz. Skipping.")

    return moved_ids

def remove_unwanted(moved_ids):
    if not moved_ids:
        logger.info("🧹 No new data was moved. Nothing to clear from local.")
        return

    logger.info(f"🧹 Cleaning up {len(moved_ids)} items from local ChromaDB...")
    collection.delete(ids=moved_ids)
    logger.info("✨ Local database cleaned.")

async def main():
    await validate_environment_and_keys()
    tool_queue = asyncio.Queue(maxsize=100)
    target_url = "https://www.aixploria.com/en/ultimate-list-ai/"

    producer_task = asyncio.create_task(producer(tool_queue, target_url))
    consumer_task = asyncio.create_task(consumer(tool_queue))

    await consumer_task
    if not producer_task.done():
        producer_task.cancel()

if __name__ == "__main__":
    if "--zilliz" in sys.argv:
        local_data = collection.get(include=['embeddings', 'metadatas', 'documents'])
        import asyncio
        loop = asyncio.get_event_loop()
        ids_migrated = loop.run_until_complete(move_to_zilliz())
        
        if "--remove-unwanted" in sys.argv:
            remove_unwanted(ids_migrated)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user. Progress is saved.")
    except Exception as e:
        traceback.print_exc()
        