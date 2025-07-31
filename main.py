import os
import streamlit as st
from dotenv import load_dotenv
import requests
import json
from typing import List, Dict
import pickle
from datetime import datetime

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# Try to import mem0, if it fails, use local memory storage
try:
    from mem0 import MemoryClient
    USE_MEM0 = True
    memory_client = MemoryClient(api_key=MEM0_API_KEY) if MEM0_API_KEY else None
except ImportError:
    USE_MEM0 = False
    memory_client = None
    st.warning("⚠️ mem0 package not found. Using local memory storage instead.")

class LocalMemory:
    """Local memory storage as fallback when mem0 is not available"""
    
    def __init__(self, storage_file="memory_storage.pkl"):
        self.storage_file = storage_file
        self.memories = self.load_memories()
    
    def load_memories(self) -> Dict:
        """Load memories from local file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            st.error(f"Error loading memories: {e}")
        return {}
    
    def save_memories(self):
        """Save memories to local file"""
        try:
            with open(self.storage_file, 'wb') as f:
                pickle.dump(self.memories, f)
        except Exception as e:
            st.error(f"Error saving memories: {e}")
    
    def add(self, messages: List[Dict], user_id: str, **kwargs):
        """Add messages to memory"""
        if user_id not in self.memories:
            self.memories[user_id] = []
        
        for message in messages:
            memory_entry = {
                "content": message["content"],
                "role": message["role"],
                "timestamp": datetime.now().isoformat(),
                "memory": f"{message['role']}: {message['content']}"
            }
            self.memories[user_id].append(memory_entry)
        
        self.save_memories()
    
    def search(self, query: str, user_id: str, limit: int = 3) -> Dict:
        """Search memories for relevant content"""
        if user_id not in self.memories:
            return {"results": []}
        
        user_memories = self.memories[user_id]
        
        # Simple keyword-based search
        query_words = query.lower().split()
        scored_memories = []
        
        for memory in user_memories:
            content = memory["content"].lower()
            score = sum(1 for word in query_words if word in content)
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by relevance and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        results = [memory for _, memory in scored_memories[:limit]]
        
        return {"results": results}

# Initialize memory system
if USE_MEM0 and memory_client:
    memory = memory_client
    st.success("✅ Using Mem0 cloud memory service")
else:
    memory = LocalMemory()
    st.info("ℹ️ Using local memory storage")

def groq_chat(prompt: str, messages: List[Dict] = None) -> str:
    """Send chat request to Groq API"""
    if messages is None:
        messages = []
    
    if not GROQ_API_KEY:
        return "❌ GROQ_API_KEY not found in environment variables"
    
    url = "https://api.groq.ai/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": messages + [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"❌ Error communicating with Groq API: {str(e)}"
    except KeyError as e:
        return f"❌ Unexpected API response format: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# Streamlit UI
st.title("🤖 Chatbot with Persistent Memory")
st.markdown("---")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    user_id = st.text_input("User ID:", value="default_user", help="Enter a unique user ID for memory isolation")
    
    st.header("Memory System Status")
    if USE_MEM0 and memory_client:
        st.success("Using Mem0 Cloud")
    else:
        st.info("Using Local Storage")
    
    # Clear memory button
    if st.button("🗑️ Clear Memory", help="Clear all stored memories for this user"):
        if USE_MEM0 and memory_client:
            # Note: Mem0 doesn't have a direct clear method, you might need to implement this
            st.warning("Clear function not implemented for Mem0. Please check Mem0 documentation.")
        else:
            if user_id in memory.memories:
                del memory.memories[user_id]
                memory.save_memories()
                st.success("Memory cleared!")
        st.experimental_rerun()

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []

# Chat input
st.subheader("💬 Chat")
user_input = st.text_input("You:", key="input", placeholder="Type your message here...")

col1, col2 = st.columns([1, 4])
with col1:
    send_button = st.button("Send 📤", use_container_width=True)

# Process user input
if send_button and user_input:
    with st.spinner("🔍 Searching memories and generating response..."):
        try:
            # Search for relevant memories
            search_results = memory.search(query=user_input, user_id=user_id, limit=3)
            memories = search_results.get("results", [])
            
            # Create context from memories
            if memories:
                memory_text = "\n".join(f"- {m.get('memory', m.get('content', ''))}" for m in memories)
                system_prompt = f"""You are a helpful AI assistant with access to previous conversation memories.

Here are relevant memories from our past conversations:
{memory_text}

Please use this context to provide more personalized and relevant responses. If the memories are relevant to the current question, reference them naturally in your response."""
            else:
                system_prompt = "You are a helpful AI assistant. Provide clear and helpful responses to user questions."
            
            # Prepare messages for API call
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent conversation history (last 5 exchanges to avoid token limits)
            recent_history = st.session_state.history[-10:] if len(st.session_state.history) > 10 else st.session_state.history
            for msg in recent_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Get AI response
            ai_response = groq_chat(user_input, messages)
            
            # Update session history
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.history.append({"role": "assistant", "content": ai_response})
            
            # Store in memory
            memory_messages = [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": ai_response}
            ]
            
            if USE_MEM0 and memory_client:
                memory.add(messages=memory_messages, user_id=user_id, version="v2")
            else:
                memory.add(messages=memory_messages, user_id=user_id)
                
        except Exception as e:
            st.error(f"❌ Error processing your request: {str(e)}")

# Display conversation history
st.subheader("📝 Conversation History")
if st.session_state.history:
    for i, msg in enumerate(st.session_state.history):
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
else:
    st.info("No conversation history yet. Start chatting!")

# Display memory status
with st.expander("🧠 Memory Status", expanded=False):
    if USE_MEM0 and memory_client:
        st.write("Using Mem0 cloud service for memory storage")
        # Try to get memory count (if supported by your mem0 version)
        try:
            search_all = memory.search(query="", user_id=user_id, limit=100)
            memory_count = len(search_all.get("results", []))
            st.write(f"Stored memories: {memory_count}")
        except:
            st.write("Memory count unavailable")
    else:
        user_memories = memory.memories.get(user_id, [])
        st.write(f"Stored memories: {len(user_memories)}")
        if user_memories:
            st.write("Recent memories:")
            for mem in user_memories[-3:]:  # Show last 3 memories
                st.write(f"- {mem.get('memory', mem.get('content', ''))[:100]}...")

# Footer
st.markdown("---")
st.markdown("💡 **Tip:** This chatbot remembers your conversations! The more you chat, the better it gets at understanding your preferences and context.")

# Environment check
if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found in environment variables. Please add it to your .env file.")

if USE_MEM0 and not MEM0_API_KEY:
    st.warning("⚠️ MEM0_API_KEY not found. Using local memory storage instead.")