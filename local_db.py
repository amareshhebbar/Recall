import chromadb
from chromadb.utils import embedding_functions
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Sequence
import operator
import json

print("🔌 Connecting to local ChromaDB...")
client = chromadb.PersistentClient(path="./chroma_db")
default_ef = embedding_functions.DefaultEmbeddingFunction()

try:
    collection = client.get_collection(name="ai_tools", embedding_function=default_ef)
except Exception as e:
    print("❌ Could not find the 'ai_tools' collection. Are you sure data was saved?")
    exit()

print("\n" + "="*40)
print("📊 DATABASE INSPECTION REPORT")
print("="*40)

count = collection.count()
print(f"Total AI Tools stored: {count}")

if count > 0:
    print("\n🔍 Peeking at the first entry to verify structure...")
    peek_data = collection.peek(1)
    
    print(f"\nID (Name): {peek_data['ids'][0]}")
    print(f"Metadata : {json.dumps(peek_data['metadatas'][0], indent=2)}")
    print(f"Document : {peek_data['documents'][0][:150]}... [TRUNCATED]")

print("\n✅ Database check complete. Everything looks properly stored." if count > 0 else "⚠️ Database is empty.")

if count == 0:
    exit()

print("\n⚙️ Initializing LangGraph Agent...")

llm = ChatOllama(model="llama3.1:8b", temperature=0.2)

class RAGState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    context: str

def retrieve_node(state: RAGState):
    latest_message = state["messages"][-1].content
    
    results = collection.query(
        query_texts=[latest_message],
        n_results=3
    )
    
    if not results['documents'][0]:
        context = "No relevant tools found in the database."
    else:
        context_chunks = []
        for i in range(len(results['documents'][0])):
            tool_name = results['ids'][0][i]
            tool_desc = results['documents'][0][i]
            tool_url = results['metadatas'][0][i].get('url', 'No URL provided')
            context_chunks.append(f"Tool: {tool_name}\nURL: {tool_url}\nDescription: {tool_desc}")
            
        context = "\n\n".join(context_chunks)
        
    return {"context": context}

def generate_node(state: RAGState):
    context = state["context"]
    system_prompt = SystemMessage(content=f"""
    You are a helpful AI tools assistant. Use the following context retrieved from my local database to answer the user's questions. 
    If the answer is not in the context, clearly state that you don't have enough information in the database.
    
    CONTEXT:
    {context}
    """)
    
    conversation = [system_prompt] + state["messages"]
    
    response = llm.invoke(conversation)
    return {"messages": [response]}

workflow = StateGraph(RAGState)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

agent = workflow.compile()

print("\n" + "="*40)
print("🤖 LANGGRAPH RAG CHAT (Powered by Ollama)")
print("="*40)
print("Type 'exit' or 'quit' to stop.\n")

chat_history = []

while True:
    user_query = input("\n🧑 Ask about the AI tools: ")
    
    if user_query.lower() in ['exit', 'quit']:
        print("Goodbye!")
        break
        
    if not user_query.strip():
        continue
        
    print("🔍 Searching and thinking...")
    
    new_message = HumanMessage(content=user_query)
    
    final_state = agent.invoke({"messages": chat_history + [new_message]})
    
    ai_response = final_state["messages"][-1].content
    
    chat_history = final_state["messages"]
    
    print("\n🤖 Response:")
    print("-" * 40)
    print(ai_response)
    print("-" * 40)