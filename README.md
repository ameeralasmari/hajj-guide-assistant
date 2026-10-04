# Hajj & Umrah Guide Assistant

A bilingual (Arabic / English) chatbot that gives pilgrims practical, general guidance:
packing, getting around, heat and crowd safety, lost-group situations and how to find
official services.

Built with **Python, Streamlit and the Gemini API (Google AI)**.

## Why I built it
I worked two Hajj seasons helping pilgrims with translation, guidance and complaint
resolution. The same questions came up again and again, often from people who were tired,
stressed and far from home. This project explores how an AI assistant could answer those
common questions quickly, in the pilgrim's own language.

## What it does
- Answers in the language the user writes in (Arabic or English)
- Keeps answers short and practical
- Refuses to give religious rulings and points users to scholars and official channels
- Sends users to official sources (Nusuk, Ministry of Hajj and Umrah) instead of guessing
- Directs emergencies to emergency services
- Retries when the AI service is busy and automatically falls back to another Gemini Flash model
- Keeps a chat history with a New chat button (saved locally in `chats.json`; on the hosted demo it lasts only for your browser session, for privacy)
- Clean, minimal design in white, Hajj green and gold, with an animated Kaaba while it thinks

## How it works
A single system prompt defines the assistant's scope and safety rules. The full chat
history is sent to Gemini on every turn, so follow-up questions keep their context.
The interface is a Streamlit chat page. A welcome screen with example questions appears at the start of every new chat, and the theme lives in `.streamlit/config.toml`.

## Run it locally
```bash
git clone https://github.com/<your-username>/hajj-guide-assistant.git
cd hajj-guide-assistant
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then add your Gemini API key from Google AI Studio
streamlit run app.py
```

## Limitations
- It has no live data, so it can't confirm permits, prices or opening hours
- It can make mistakes; always check official sources for anything important
- It gives general guidance only, never religious rulings

## Ideas for next steps
- Ground answers in official documents (retrieval over Ministry guidance)
- Add more languages (Urdu, Indonesian, Turkish)
- Add voice input for pilgrims who can't type easily
