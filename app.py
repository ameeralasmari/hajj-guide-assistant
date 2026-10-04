"""Hajj & Umrah Guide Assistant
A bilingual (Arabic / English) chatbot that gives pilgrims practical, general
guidance, built with Streamlit and the Gemini API.
Chats are saved locally in chats.json so the history survives restarts.
"""
import json
import os
import re
import time
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
CHATS_FILE = Path(__file__).with_name("chats.json")
# On Streamlit Community Cloud every visitor shares the same server, so chats are
# NOT saved to disk there (that would show one visitor's chats to another).
ON_CLOUD = Path(__file__).resolve().as_posix().startswith("/mount/src")
USER_AVATAR, BOT_AVATAR = "🤲", "🕋"

SYSTEM_PROMPT = """You are a friendly guide assistant for pilgrims performing Hajj and Umrah in Saudi Arabia.

Scope: practical help only, such as getting around, preparing for the trip, crowd and heat tips,
etiquette, lost-item and lost-group situations, and how to find official services.

Rules:
1. Reply in the same language the user writes in (Arabic or English). Keep answers short, clear and kind.
2. Do NOT give religious rulings (fatwas). For questions about how to perform rituals correctly or
   whether something is permissible, say you can't rule on it and point the user to the scholars and
   guides available on site or through official channels.
3. For permits, bookings and official services, point to the official Nusuk platform and the
   Ministry of Hajj and Umrah. Never invent prices, dates, rules, phone numbers or opening hours.
   If you are not sure, say so and suggest checking the official source.
4. In any emergency or medical situation, tell the user to contact emergency services (911) or the
   nearest official staff or medical point immediately.
5. Stay on topic. If asked about something unrelated, politely steer back to Hajj and Umrah help.
"""

CHIPS = [
    ("🎒 Packing", "What should I pack for Umrah in summer?"),
    ("🧭 Lost group", "ضاع مني أحد أفراد مجموعتي في الحرم، ماذا أفعل؟"),
    ("☀️ Heat safety", "How do I stay safe from heat during Hajj?"),
    ("🪪 Permits", "كيف أحجز تصريح العمرة؟"),
]

# ---------- Look and feel (clean white, Hajj green, gold and black) ----------
CSS = """<style>
footer{visibility:hidden;}
.block-container{max-width:780px;padding-top:2rem;}
[data-testid="stSidebar"]{background:#F6F3EA;border-right:1px solid #E6E0CE;}
.brand{font-size:1.15rem;font-weight:700;color:#073D22;padding:.2rem .3rem .8rem;}
.side-label{font-size:.75rem;letter-spacing:.08em;color:#8a8570;margin:1rem 0 .3rem .3rem;text-transform:uppercase;}
[data-testid="stSidebar"] .stButton>button{background:transparent;border:none;box-shadow:none;color:#1B1B1B;justify-content:flex-start;text-align:left;border-radius:10px;font-weight:400;}
[data-testid="stSidebar"] .stButton>button:hover{background:#E9E4D3;}
[data-testid="stSidebar"] .stButton:first-of-type>button{background:#E9E4D3;font-weight:600;}
.greet-ar{text-align:center;font-size:1.1rem;color:#B8921F;margin-top:.2rem;}
.greet{text-align:center;font-family:Georgia,'Times New Roman',serif;font-size:2.3rem;color:#073D22;margin:.2rem 0 .3rem;}
.rule{width:56px;height:3px;background:#C9A227;border-radius:2px;margin:0 auto 1.4rem;}
.foot{text-align:center;color:#8a8570;font-size:.78rem;margin-top:2.5rem;line-height:1.6;}
.stMain .stButton>button{border:1px solid #E3DCC8;border-radius:999px;background:#fff;color:#1B1B1B;font-size:.85rem;font-weight:400;}
.stMain .stButton>button:hover{border-color:#C9A227;background:#FBF6E3;color:#073D22;}
[data-testid="stChatInput"]{border-radius:26px;border:1px solid #E3DCC8;background:#fff;box-shadow:0 4px 18px rgba(11,107,58,.08);}
[data-testid="stChatInput"]:focus-within{border-color:#C9A227;}
[data-testid="stChatMessage"]{background:transparent;border:none;padding:.6rem 0;}
[data-testid="stChatMessage"] p{unicode-bidi:plaintext;text-align:start;line-height:1.75;}
.kaaba-wrap{position:relative;width:120px;height:120px;margin:0 auto;}
.kaaba{position:absolute;left:35px;top:38px;width:50px;height:50px;background:#000;border-radius:3px;box-shadow:0 4px 14px rgba(0,0,0,.25);animation:glow 2.6s ease-in-out infinite;}
.kaaba::before{content:"";position:absolute;left:0;right:0;top:10px;height:9px;background:linear-gradient(90deg,#8a6d14,#E6C75A,#8a6d14);}
.kaaba::after{content:"";position:absolute;left:19px;top:28px;width:12px;height:22px;background:#C9A227;border-radius:2px 2px 0 0;}
.orbit{position:absolute;inset:0;animation:spin 6s linear infinite;}
.orbit i{position:absolute;left:56px;top:2px;width:8px;height:8px;border-radius:50%;background:#C9A227;box-shadow:0 0 6px rgba(201,162,39,.8);transform-origin:4px 58px;}
.orbit i:nth-child(2){transform:rotate(120deg);}
.orbit i:nth-child(3){transform:rotate(240deg);}
.loading{padding:.2rem 0;}
.loading .kaaba-wrap{transform:scale(.5);margin:-24px 0 -24px -22px;}
.loading-text{color:#0B6B3A;font-size:.95rem;}
@keyframes spin{to{transform:rotate(360deg);}}
@keyframes glow{0%,100%{box-shadow:0 4px 14px rgba(0,0,0,.25);}50%{box-shadow:0 0 24px rgba(201,162,39,.85);}}
</style>"""

KAABA = '<div class="kaaba-wrap"><div class="orbit"><i></i><i></i><i></i></div><div class="kaaba"></div></div>'
LOADING = f'<div class="loading">{KAABA}<div class="loading-text">جارٍ تجهيز الإجابة… | Preparing your answer…</div></div>'
WELCOME = f'{KAABA}<div class="greet-ar">السلام عليكم ورحمة الله</div><div class="greet">How can I help you?</div><div class="rule"></div>'
FOOTER = '<div class="foot">AI can make mistakes. For permits and official services, check the Nusuk platform<br>and the Ministry of Hajj and Umrah.</div>'


# ---------- Chat history (saved to chats.json) ----------
def load_chats():
    if not ON_CLOUD and CHATS_FILE.exists():
        try:
            return json.loads(CHATS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_chats():
    if ON_CLOUD:
        return
    try:
        CHATS_FILE.write_text(
            json.dumps(st.session_state.chats, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


# ---------- Gemini ----------
@st.cache_resource
def fallback_models(_client):
    """Other Gemini Flash models this key can use, tried if the main model is busy."""
    names = []
    try:
        for m in _client.models.list():
            name = m.name.removeprefix("models/")
            ok = "generateContent" in (m.supported_actions or [])
            skip = any(w in name for w in ("image", "tts", "live", "audio", "embedding"))
            if "flash" in name and ok and not skip:
                names.append(name)
    except Exception:
        pass
    return [n for n in sorted(set(names), reverse=True) if n != MODEL][:2]


def retry_delay(exc):
    """Seconds Google asks us to wait on a rate-limit error (None if not given)."""
    m = re.search(r"retry(?:Delay\W+|\s+in\s+)(\d+(?:\.\d+)?)s", str(exc))
    return float(m.group(1)) if m else None


def ask_gemini(client, messages):
    # Gemini uses the role "model" for the assistant.
    recent = messages[-12:]  # keep requests small
    while recent and recent[0]["role"] != "user":
        recent = recent[1:]
    history = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["text"])],
        )
        for m in recent
    ]
    last = None  # the last busy/limit error, so we can tell the user what happened
    for model in [MODEL] + fallback_models(client):
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=history,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                return response.text or "Sorry, I couldn't generate an answer. Please try again."
            except errors.APIError as exc:
                if exc.code == 503:  # overloaded: wait a moment and retry once
                    last = exc
                    time.sleep(2)
                    continue
                wait = retry_delay(exc) if exc.code == 429 else None
                if wait is not None and wait <= 20 and attempt == 0:
                    last = exc  # per-minute limit: wait the time Google asks for, then retry
                    time.sleep(wait + 1)
                    continue
                if exc.code in (404, 429):  # model missing or limit reached: try the next model
                    last = exc
                    break
                return f"Something went wrong: {exc}"
            except Exception as exc:  # network problems, etc.
                return f"Something went wrong: {exc}"
    if last is None:
        return "No AI model is available. Check GEMINI_MODEL in your .env file."
    detail = f"(error {last.code} {last.status})"
    if last.code == 429:
        return f"The free usage limit has been reached for now. Please try again in a few minutes. {detail}"
    return f"The AI service is very busy right now. Please send your message again in a minute. {detail}"


# ---------- Page ----------
st.set_page_config(page_title="Hajj & Umrah Guide", page_icon="🕋")
st.markdown(CSS, unsafe_allow_html=True)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Missing GEMINI_API_KEY. Copy .env.example to .env and add your key.")
    st.stop()
client = genai.Client(api_key=api_key)

if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
    st.session_state.current = None
chats = st.session_state.chats


def submit(text):
    """Add the user's message to the current chat (creating one if needed) and rerun."""
    if st.session_state.current is None:
        cid = uuid.uuid4().hex[:8]
        title = text[:40] + ("…" if len(text) > 40 else "")
        chats[cid] = {"title": title, "messages": []}
        st.session_state.current = cid
    chats[st.session_state.current]["messages"].append({"role": "user", "text": text})
    save_chats()
    st.rerun()


# Sidebar: brand, new chat, history
with st.sidebar:
    st.markdown('<div class="brand">🕋 Hajj &amp; Umrah Guide</div>', unsafe_allow_html=True)
    if st.button("＋  New chat", use_container_width=True):
        st.session_state.current = None
        st.rerun()
    st.markdown('<div class="side-label">Chat history</div>', unsafe_allow_html=True)
    if not chats:
        st.caption("No chats yet")
    for cid, chat in reversed(list(chats.items())):
        col_open, col_del = st.columns([6, 1])
        label = ("● " if cid == st.session_state.current else "") + chat["title"]
        if col_open.button(label, key=f"open_{cid}", use_container_width=True):
            st.session_state.current = cid
            st.rerun()
        if col_del.button("🗑", key=f"del_{cid}"):
            del chats[cid]
            if st.session_state.current == cid:
                st.session_state.current = None
            save_chats()
            st.rerun()

current = st.session_state.current
messages = chats[current]["messages"] if current else []

if not messages:
    # Welcome screen: greeting, centered input and suggestion chips
    st.markdown("<div style='height:7vh'></div>", unsafe_allow_html=True)
    st.markdown(WELCOME, unsafe_allow_html=True)
    with st.container():  # inside a container the input stays in the middle of the page
        text = st.chat_input("Ask anything / اسأل أي شيء", key="welcome_input")
    if text:
        submit(text)
    cols = st.columns(len(CHIPS))
    for col, (label, question) in zip(cols, CHIPS):
        if col.button(label, key=f"chip_{label}", use_container_width=True):
            submit(question)
    st.markdown(FOOTER, unsafe_allow_html=True)
else:
    for msg in messages:
        avatar = USER_AVATAR if msg["role"] == "user" else BOT_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["text"])

    text = st.chat_input("Ask anything / اسأل أي شيء", key="chat_input")
    if text:
        submit(text)

    # If the last message is from the user, it still needs an answer
    if messages[-1]["role"] == "user":
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            slot = st.empty()
            slot.markdown(LOADING, unsafe_allow_html=True)
            answer = ask_gemini(client, messages)
            slot.markdown(answer)
        messages.append({"role": "assistant", "text": answer})
        save_chats()
