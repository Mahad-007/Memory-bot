import os
import streamlit as st
from dotenv import load_dotenv
from mem0 import MemoryClient
import requests
# from mem0 import Memory


load_dotenv()

MEM0_API_KEY = os.getenv("MEM0_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

memory = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

def groq_chat(prompt, messages=[]):
    url = "https://api.groq.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": "mixtral-8x7b-32768", "messages": messages + [{"role": "user", "content": prompt}]}
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

st.title("Chatbot with Persistent Memory")

user_id = "default_user"

if "history" not in st.session_state:
    st.session_state.history = []

inp = st.text_input("You:", key="input")
if st.button("Send") and inp:
    search_res = memory.search(query=inp, user_id=user_id, limit=3)
    # search results structure: {"results": [...] }
    memories = search_res.get("results", [])
    mem_text = "\n".join(f"- {m['memory']}" for m in memories)
    system_prompt = f"Here are relevant user memories:\n{mem_text}\n\nNow respond to the user's message."

    messages = [{"role": "system", "content": system_prompt}]
    for h in st.session_state.history:
        messages.append({"role": h["role"], "content": h["content"]})

    reply = groq_chat(inp, messages)

    st.session_state.history.append({"role": "user", "content": inp})
    st.session_state.history.append({"role": "assistant", "content": reply})

    memory.add(messages=[{"role": "user", "content": inp}, {"role": "assistant", "content": reply}],
               user_id=user_id, version="v2")

for msg in st.session_state.history:
    speaker = "🗣️You" if msg["role"] == "user" else "🤖Bot"
    st.write(f"**{speaker}:** {msg['content']}")






# ADDING MEMORY
# messages = [
#     { "role": "user", "content": "Hi, I'm Alex. I'm a vegetarian and I'm allergic to nuts." },
#     { "role": "assistant", "content": "Hello Alex! I see that you're a vegetarian with a nut allergy." }
# ]

# client.add(messages, user_id="alex")


# RETRIEVAL
# query = "What can I cook for dinner tonight?"
# client.search(query, user_id="alex")