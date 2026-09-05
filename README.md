# Voice-to-Text Food Ordering Agent

An AI voice agent that takes food orders over a call, built for [Hackathon name].
Rime provides the primary spoken output; the agent listens, understands orders,
and handles mid-call corrections without losing context.

## Problem & User
A caller places a food order by voice, the same way they'd call a restaurant.
The agent must sound natural, take the order correctly, and — critically —
handle real conversational behavior like the caller correcting themselves
mid-response, which is common on real phone calls.

## Architecture
- **Transport / orchestration:** LiveKit Agents
- **Speech-to-text:** Deepgram
- **LLM (order logic / corrections):** Groq — model: [GROQ_MODEL from your .env, 
  e.g. openai/gpt-oss-120b]
- **Text-to-speech:** Rime — model: [exact model ID], voice: [speaker name], 
  language: [e.g. en]
- **Audio format / endpoint:** [fill in — e.g. mulaw 8kHz over LiveKit's 
  default endpoint, or whichever endpoint you configured]

Flow: caller speaks → Deepgram transcribes → Groq LLM interprets against 
menu + current order state → order_logic.py updates state → response text 
sent to Rime → Rime audio streamed back to caller.

## Setup Instructions
1. Clone the repo
2. Create a virtual environment: `python -m venv venv`
3. Activate it and run `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your own API keys (Rime, 
   LiveKit, Deepgram, Groq)
5. Run the agent: `python voice_pipeline/agent.py dev`
6. Connect via [LiveKit Playground / your frontend] to test

## Third-Party Services Used
- Rime (text-to-speech)
- LiveKit Cloud (realtime transport)
- Deepgram (speech-to-text)
- Groq (LLM inference)

## Hard Voice Problem Addressed
Conversation continuity / interruption handling — see RIME_EVIDENCE.md for 
the acceptance test and results.

## Known Limitations
[fill in once testing is done — e.g. "double interruptions in quick 
succession aren't yet handled" or whatever you discover]

## Failure Behavior
[what happens if Deepgram/Groq/Rime is unreachable — does it fail silently, 
retry, or tell the caller? Fill this in honestly, even if it's currently 
"not yet handled — known limitation"]