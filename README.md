# Recall
<p align="center">
<img src="https://img.shields.io/badge/Framework-React_Native_%2B_Expo-0081ff?style=for-the-badge" />
<img src="https://img.shields.io/badge/Intelligence-100%25_Offline-green?style=for-the-badge" />
<img src="https://img.shields.io/badge/Backend-Python_Agentic_Pipeline-yellow?style=for-the-badge" />
</p>

```json
{ 
  "project": "Recall", 
  "frameworks": ["Python", "LangGraph", "Ollama"],
  "manual_data_entry": null 
}
```

Recall is a highly autonomous, multi-layered data extraction and RAG (Retrieval-Augmented Generation) pipeline. You point it at a URL, and it doesn't just scrape the page—it reads it, cross-references it with live web searches, extracts structured JSON using local LLMs, and stores it in both local and cloud vector databases so you can chat with it later.

And one more thing, this doesn;t have any ui cause it doesn;t need one
---

### Explore the *MIGRATED* docs

<details name="recall-tabs">
<summary><b>Wanna start</b> </summary>
<br>

The straight-up way to get this pipeline running on your machine.


## 1. Create and Activate Virtual Environment
Keeping dependencies isolated is best practice. Run the following commands in your terminal:

### **For macOS/Linux:**
```bash
python3.13 -m venv venv
source venv/bin/activate
```


> **Note:** Once activated, you should see `(venv)` appear at the start of your terminal prompt.

---

## 2. Install Requirements
With the environment active, install all necessary libraries defined in the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

*or for the Fedora System*
```bash
python3 -m pip install -r requirements.txt
```

*If this is your first time using Playwright, you may also need to install the browser binaries:*
```bash
playwright install chromium
```

---

## 3. Run the Script
Now that your environment is configured, launch the main script:

```bash
python index.py
```

---

## Output Data
After the script completes, you can find the extracted data (and HTML content, if configured) in the following directory:
* `storage/datasets/default/`

---

4. Fire it up

Run the main scraper and enrichment script:


```bash
python main.py
```
Want to migrate your local ChromaDB data to the Zilliz cloud? Just pass the flag:


```bash
python main.py --zilliz --remove-unwanted
```
</details>

---

<details name="recall-tabs">
<summary><b>[[[ How's it Working ]]]</b></summary>


Recall is built like a factory assembly line using asynchronous Python. Here is what happens under the hood:

The Crawler (Producer): Crawl4AI visits the target website, bypasses caching, and rips out the raw Markdown. It splits massive pages into manageable chunks and tosses them into an async queue.

The Search Layers: Before trusting the scraped data, the system attempts to ground it. It will try to use Gemini to search the web. If that fails, it cascades down to Serper, Tavily, Brave, and finally DuckDuckGo.

The Brain (Enrichment): The raw data and the web search results are fed into Ollama (Llama 3.1) locally via LangGraph. Ollama synthesizes the messy text into a perfectly structured JSON object (Pros, Cons, Descriptions, Pricing).

The Vault: The cleaned data is instantly embedded into a local ChromaDB database. It can also be synced to a Zilliz (Milvus) cloud cluster.

The Chat: Once the data is stored, you can run the LangGraph RAG terminal chat. You ask a question, it queries ChromaDB, retrieves the exact context, and Ollama talks to you like a friend about the tools it just researched.

</details>

---

<details name="recall-tabs">
<summary><b>The Tech Stack</b></summary>


I didn't use off-the-shelf wrappers; I built a custom pipeline. Here are the core tools making this happen:

- Crawl4AI: For hardcore, headless browser DOM extraction.

LangGraph: To build the cyclic graphs for my research agents and chat loops.

Ollama (llama3.1:8b): The local heavyweight champion doing all the JSON formatting and conversational generation for free.

ChromaDB: My local vector database for fast, offline RAG.

Zilliz (PyMilvus): The cloud vector database for production-level storage.

LiteLLM / Playwright: Used in the agentic extraction script to let the AI physically click buttons, navigate Cloudflare blocks, and hunt down data autonomously.

</details>

---

<details name="recall-tabs">
<summary><b>State & Duplicate Management</b></summary>


Scraping gets messy fast. To prevent extracting the same data twice or corrupting the database, Recall uses a strict StateManager.

Deterministic Hashing: Every extracted entity generates a unique SHA-256 hash based on its name.

Smart Upserting: If the crawler finds a tool it already knows about, it doesn't create a duplicate. It merges the new metrics and appends new sentiment analysis to the existing record.

Local Checkpointing: It writes processed names to processed_tools.txt so if the script crashes, you don't lose your API credits starting over.

</details>

---

<details name="recall-tabs">
<summary><b> [[[ Updates needed ]]]</b></summary>


The pipeline is currently a highly functional MVP, but here is what is on the roadmap for future updates:

Full Agentic UI Automation: Enhancing the human_click logic to let the AI solve CAPTCHAs and navigate deep paginated directories completely on its own.

Front-End Integration: Hooking up this massive backend vector database to a React Native / Next.js frontend for easy searching.

Dynamic Model Switching: Automatically swapping between smaller local models for simple data extraction and heavy cloud models (like Claude 3.5 or GPT-4o) for complex reasoning tasks depending on the API keys available.

</details>


```
```


#### *Congratulations, you’ve built a $50-a-month subscription to local LLM tokens just to recreate the 'Save as PDF' button*# Recall

<!-- docs pass: 2026-07-03T04:33:39Z -->

< docs pass retry: 2026-07-03T04:44:42Z -->
