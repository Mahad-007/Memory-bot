import os
import streamlit as st
from dotenv import load_dotenv
import requests
import json
from typing import List, Dict, Any, Optional, Union
import pickle
from datetime import datetime
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# Try to import mem0, if it fails, use local memory storage
try:
    from mem0 import MemoryClient
    USE_MEM0 = True
    memory_client = MemoryClient(api_key=MEM0_API_KEY) if MEM0_API_KEY else None
    logger.info("Mem0 successfully imported")
except ImportError as e:
    USE_MEM0 = False
    memory_client = None
    logger.warning(f"Mem0 import failed: {e}")
except Exception as e:
    USE_MEM0 = False
    memory_client = None
    logger.error(f"Unexpected error importing Mem0: {e}")

class SafeDict:
    """Safe dictionary wrapper to handle missing keys gracefully"""
    
    def __init__(self, data: Any):
        if isinstance(data, dict):
            self.data = data
        elif isinstance(data, list):
            self.data = {"results": data}
        else:
            self.data = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Safely get value from dictionary"""
        try:
            return self.data.get(key, default)
        except AttributeError:
            return default
    
    def __getitem__(self, key: str) -> Any:
        """Safely get item from dictionary"""
        try:
            return self.data[key]
        except (KeyError, TypeError):
            return None

class LocalMemory:
    """Local memory storage as fallback when mem0 is not available"""
    
    def __init__(self, storage_file: str = "memory_storage.pkl"):
        self.storage_file = storage_file
        self.memories = self._load_memories()
    
    def _load_memories(self) -> Dict[str, List[Dict]]:
        """Load memories from local file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'rb') as f:
                    data = pickle.load(f)
                    # Ensure data is a dictionary
                    return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
        return {}
    
    def _save_memories(self) -> bool:
        """Save memories to local file"""
        try:
            with open(self.storage_file, 'wb') as f:
                pickle.dump(self.memories, f)
            return True
        except Exception as e:
            logger.error(f"Error saving memories: {e}")
            return False
    
    def add(self, messages: Union[List[Dict], Dict], user_id: str, **kwargs) -> bool:
        """Add messages to memory"""
        try:
            # Ensure messages is a list
            if isinstance(messages, dict):
                messages = [messages]
            elif not isinstance(messages, list):
                logger.error(f"Invalid messages type: {type(messages)}")
                return False
            
            # Initialize user memory if not exists
            if user_id not in self.memories:
                self.memories[user_id] = []
            
            # Process each message
            for message in messages:
                if not isinstance(message, dict):
                    continue
                
                content = message.get("content", "")
                role = message.get("role", "unknown")
                
                memory_entry = {
                    "content": str(content),
                    "role": str(role),
                    "timestamp": datetime.now().isoformat(),
                    "memory": f"{role}: {content}"
                }
                self.memories[user_id].append(memory_entry)
            
            return self._save_memories()
            
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return False
    
    def search(self, query: str, user_id: str, limit: int = 3) -> Dict[str, List[Dict]]:
        """Search memories for relevant content"""
        try:
            if not isinstance(query, str):
                query = str(query)
            
            if not isinstance(user_id, str):
                user_id = str(user_id)
            
            if user_id not in self.memories:
                return {"results": []}
            
            user_memories = self.memories[user_id]
            if not isinstance(user_memories, list):
                return {"results": []}
            
            # Simple keyword-based search
            query_words = query.lower().split()
            scored_memories = []
            
            for memory in user_memories:
                if not isinstance(memory, dict):
                    continue
                    
                content = str(memory.get("content", "")).lower()
                score = sum(1 for word in query_words if word in content)
                
                if score > 0:
                    scored_memories.append((score, memory))
            
            # Sort by relevance and return top results
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            results = [memory for _, memory in scored_memories[:limit]]
            
            return {"results": results}
            
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return {"results": []}

class Mem0Wrapper:
    """Wrapper for Mem0 client with error handling"""
    
    def __init__(self, client):
        self.client = client
    
    def add(self, messages: Union[List[Dict], Dict], user_id: str, **kwargs) -> bool:
        """Add messages to Mem0 with error handling"""
        try:
            if isinstance(messages, dict):
                messages = [messages]
            
            result = self.client.add(messages=messages, user_id=user_id, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Error adding to Mem0: {e}")
            return False
    
    def search(self, query: str, user_id: str, limit: int = 3) -> Dict[str, List[Dict]]:
        """Search Mem0 with error handling"""
        try:
            result = self.client.search(query=query, user_id=user_id, limit=limit)
            
            # Handle different response formats
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"results": result}
            else:
                return {"results": []}
                
        except Exception as e:
            logger.error(f"Error searching Mem0: {e}")
            return {"results": []}

def initialize_memory():
    """Initialize memory system with error handling"""
    try:
        if USE_MEM0 and memory_client:
            return Mem0Wrapper(memory_client), "Mem0 Cloud"
        else:
            return LocalMemory(), "Local Storage"
    except Exception as e:
        logger.error(f"Error initializing memory: {e}")
        return LocalMemory(), "Local Storage (Fallback)"

def groq_chat(prompt: str, messages: Optional[List[Dict]] = None) -> str:
    """Send chat request to Groq API with comprehensive error handling"""
    if messages is None:
        messages = []
    
    if not GROQ_API_KEY:
        return "❌ GROQ_API_KEY not found in environment variables"
    
    if not isinstance(prompt, str):
        prompt = str(prompt)
    
    try:
        # Validate and clean messages
        clean_messages = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                role = str(msg["role"]).strip().lower()
                content = str(msg["content"]).strip()
                
                # Ensure valid roles
                if role in ["system", "user", "assistant"] and content:
                    clean_messages.append({
                        "role": role,
                        "content": content
                    })
        
        # Add user message
        if prompt.strip():
            clean_messages.append({"role": "user", "content": prompt.strip()})
        
        # Use correct Groq API endpoint
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # Use a supported model
        payload = {
            "model": "llama3-8b-8192",  # Changed to a more reliable model
            "messages": clean_messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False
        }
        
        logger.info(f"Sending request to Groq API with {len(clean_messages)} messages")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # Log response details for debugging
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            error_detail = response.text
            logger.error(f"Bad request details: {error_detail}")
            return f"❌ Bad request to Groq API. Please check your API key and try again."
        
        if response.status_code == 401:
            return "❌ Invalid API key. Please check your GROQ_API_KEY in the .env file."
        
        if response.status_code == 429:
            return "❌ Rate limit exceeded. Please wait a moment and try again."
        
        response.raise_for_status()
        
        response_data = response.json()
        
        # Safely extract the response
        choices = response_data.get("choices", [])
        if not choices:
            return "❌ No response from AI model"
        
        message = choices[0].get("message", {})
        content = message.get("content", "❌ Empty response from AI")
        
        return str(content)
        
    except requests.exceptions.Timeout:
        return "❌ Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "❌ Connection error. Please check your internet connection."
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {e}")
        return f"❌ HTTP error: {e}. Please check your API key and try again."
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return "❌ Invalid response format from API"
    except Exception as e:
        logger.error(f"Unexpected error in groq_chat: {e}")
        return f"❌ Unexpected error: {str(e)}"

def safe_get_memories(memory_system, user_input: str, user_id: str) -> List[Dict]:
    """Safely get memories with error handling"""
    try:
        search_results = memory_system.search(query=user_input, user_id=user_id, limit=3)
        
        # Handle different response formats
        if isinstance(search_results, dict):
            results = search_results.get("results", [])
        elif isinstance(search_results, list):
            results = search_results
        else:
            results = []
        
        # Ensure results is a list
        if not isinstance(results, list):
            results = []
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        return []

def format_memory_text(memories: List[Dict]) -> str:
    """Safely format memory text"""
    try:
        memory_lines = []
        for memory in memories:
            if isinstance(memory, dict):
                # Try different fields for memory content
                content = (memory.get('memory') or 
                          memory.get('content') or 
                          memory.get('text') or 
                          str(memory))
                memory_lines.append(f"- {content}")
        
        return "\n".join(memory_lines)
    except Exception as e:
        logger.error(f"Error formatting memory text: {e}")
        return ""

# Initialize memory system
memory, memory_type = initialize_memory()

# Streamlit Configuration
st.set_page_config(
    page_title="AI Chatbot with Memory",
    page_icon="🤖",
    layout="wide"
)

# Main UI
st.title("🤖 AI Chatbot with Persistent Memory")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # User ID input with validation
    user_id_input = st.text_input("User ID:", value="default_user", help="Enter a unique user ID for memory isolation")
    user_id = str(user_id_input) if user_id_input else "default_user"
    
    st.header("🧠 Memory System")
    if memory_type == "Mem0 Cloud":
        st.success("✅ Using Mem0 Cloud")
    else:
        st.info(f"ℹ️ Using {memory_type}")
    
    # Memory management
    st.header("🛠️ Memory Management")
    if st.button("🗑️ Clear Memory", help="Clear all stored memories for this user"):
        try:
            if hasattr(memory, 'memories') and user_id in memory.memories:
                del memory.memories[user_id]
                memory._save_memories()
                st.success("✅ Memory cleared successfully!")
                st.rerun()
            else:
                st.info("No memories found for this user.")
        except Exception as e:
            st.error(f"❌ Error clearing memory: {e}")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []

if "processing" not in st.session_state:
    st.session_state.processing = False

# Main chat interface
col1, col2 = st.columns([4, 1])

with col1:
    user_input = st.text_input(
        "💬 Your message:", 
        key="input", 
        placeholder="Type your message here...",
        disabled=st.session_state.processing
    )

with col2:
    send_button = st.button(
        "Send 📤", 
        use_container_width=True,
        disabled=st.session_state.processing or not user_input.strip()
    )

# Process user input
if send_button and user_input.strip():
    st.session_state.processing = True
    
    with st.spinner("🔍 Processing your message..."):
        try:
            # Get relevant memories
            memories = safe_get_memories(memory, user_input, user_id)
            
            # Create system prompt
            if memories:
                memory_text = format_memory_text(memories)
                system_prompt = f"""You are a helpful AI assistant with access to previous conversation memories.

Here are relevant memories from our past conversations:
{memory_text}

Please use this context to provide more personalized and relevant responses. Reference the memories naturally if they're relevant to the current question."""
            else:
                system_prompt = "You are a helpful AI assistant. Provide clear and helpful responses to user questions."
            
            # Prepare messages for API call
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent conversation history (limit to avoid token overflow)
            recent_history = st.session_state.history[-8:] if len(st.session_state.history) > 8 else st.session_state.history
            for msg in recent_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
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
            
            # Add to memory with error handling
            success = memory.add(messages=memory_messages, user_id=user_id)
            if not success:
                st.warning("⚠️ Failed to save conversation to memory")
                
        except Exception as e:
            error_msg = f"❌ Error processing your request: {str(e)}"
            st.error(error_msg)
            logger.error(f"Processing error: {e}\n{traceback.format_exc()}")
        
        finally:
            st.session_state.processing = False
            st.rerun()

# Display conversation history
st.subheader("💬 Conversation History")

if st.session_state.history:
    for i, msg in enumerate(st.session_state.history):
        try:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.write(msg["content"])
                elif msg["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.write(msg["content"])
        except Exception as e:
            logger.error(f"Error displaying message {i}: {e}")
            continue
else:
    st.info("💡 No conversation history yet. Start chatting to see your messages here!")

# Memory status display
with st.expander("🧠 Memory Status & Debug Info", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Memory System:** {memory_type}")
        st.write(f"**User ID:** {user_id}")
        
        # Show memory count
        try:
            if hasattr(memory, 'memories'):
                user_memories = memory.memories.get(user_id, [])
                st.write(f"**Stored Memories:** {len(user_memories)}")
            else:
                st.write("**Stored Memories:** Unknown (using Mem0)")
        except Exception as e:
            st.write(f"**Memory Error:** {e}")
    
    with col2:
        st.write(f"**Session Messages:** {len(st.session_state.history)}")
        st.write(f"**GROQ API:** {'✅ Configured' if GROQ_API_KEY else '❌ Missing'}")
        st.write(f"**MEM0 API:** {'✅ Configured' if MEM0_API_KEY else '❌ Missing'}")

# Footer
st.markdown("---")
st.markdown("""
### 💡 Tips:
- This chatbot remembers your conversations across sessions
- Use different User IDs to maintain separate conversation contexts
- The AI uses your conversation history to provide more personalized responses
- Check the Memory Status section for debugging information
""")

# Environment validation warnings
if not GROQ_API_KEY:
    st.error("❌ **GROQ_API_KEY** not found in environment variables. Please add it to your .env file.")
    st.info("""
    **To get your Groq API key:**
    1. Go to https://console.groq.com/
    2. Sign up or log in
    3. Navigate to API Keys section
    4. Create a new API key
    5. Add it to your .env file as: `GROQ_API_KEY=your_key_here`
    """)

if USE_MEM0 and not MEM0_API_KEY:
    st.warning("⚠️ **MEM0_API_KEY** not found. Using local memory storage instead.")

# Test API connection button
if GROQ_API_KEY:
    if st.button("🔍 Test Groq API Connection"):
        with st.spinner("Testing API connection..."):
            test_response = groq_chat("Hello, this is a test message.", [])
            if "❌" not in test_response:
                st.success("✅ Groq API connection successful!")
            else:
                st.error(f"❌ API test failed: {test_response}")
                st.info("**Troubleshooting:**")
                st.write("1. Verify your API key is correct")
                st.write("2. Check if you have credits/quota remaining")
                st.write("3. Ensure your API key has proper permissions")

# Clear input after processing
if st.session_state.get("clear_input", False):
    st.session_state.clear_input = False