# Voice-to-Text Food Ordering Agent

An AI voice agent that takes food orders over a call, built for **DataForge**.
Rime provides the primary spoken output; the agent listens, understands orders,
and handles mid-call corrections without losing context.

## Problem & User
A caller places a food order by voice, the same way they'd call a restaurant.
The agent must sound natural, take the order correctly, and — critically —
handle real conversational behavior like the caller correcting themselves
mid-response, speaking in Hindi or English interchangeably, or asking the
agent to stop talking — all common on real phone calls.

## Architecture
- **Transport / orchestration:** LiveKit Agents
- **Speech-to-text:** Deepgram — model: `nova-3`, language: `multi` (enables
  automatic Hindi/English codeswitching detection per utterance)
- **LLM (order logic / corrections):** Groq — model: `openai/gpt-oss-120b`
  (configurable via `GROQ_MODEL` in `.env`)
- **Text-to-speech:** Rime — model: `coda`, speaker: `nadi`. Language starts
  at `eng` and is switched dynamically to `hin` (via `update_options`) when
  Deepgram detects the caller has switched to Hindi, and back again when
  they switch back to English.
- **Audio format / endpoint:** LiveKit Cloud default WebRTC transport
  (browser/Playground client) — no telephony bridge in this build; see
  Known Limitations.

Flow: caller speaks → Deepgram transcribes and detects language → agent
reads the detected language off the transcript event → Groq LLM interprets
the utterance against the menu, current order state, and detected language
→ `order_logic.py` updates state → response text sent to Rime (in the
matching language) → Rime audio streamed back to caller.

## Setup Instructions
1. Clone the repo
2. Create a virtual environment: `python -m venv venv`
3. Activate it and run `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your own API keys (Rime,
   LiveKit, Deepgram, Groq)
5. Run the agent: `python agent.py dev`
6. Connect via the LiveKit Agents Playground (printed as a link in the
   terminal output when the agent starts) to test

## Third-Party Services Used
- Rime (text-to-speech)
- LiveKit Cloud (realtime transport)
- Deepgram (speech-to-text)
- Groq (LLM inference)

## Hard Voice Problems Addressed
1. **Conversation continuity / interruption handling** — mid-response
   caller corrections are applied correctly, with stale in-flight LLM
   responses cancelled via turn-fencing rather than spoken.
2. **Multilingual and code-switched speech** — the agent detects Hindi vs.
   English per turn from Deepgram's own language detection and replies in
   the matching language, switching Rime's TTS language to match.

See `RIME_EVIDENCE.md` for acceptance tests and results for both claims,
plus the stop-command kill-switch behavior.

## Known Limitations
- The "stop" / "ruko" kill-switch is a fixed keyword match, not semantic
  understanding — it won't catch every possible phrasing a caller might
  use to ask the agent to stop.
- Language detection/switching currently maps only Hindi and English to
  Rime voice codes; other languages Deepgram's `multi` mode can detect are
  not yet mapped to a corresponding Rime language setting.
- No real telephony line (Twilio) is wired in — testing and the demo use
  LiveKit's browser-based Playground rather than an actual phone call.
- [fill in anything else you discover once full testing is complete]

## Failure Behavior
- **Groq (LLM) failures:** caught explicitly — if the Groq API call fails
  or times out, the agent replies with a short fallback ("Sorry, I'm having
  trouble right now — could you repeat that?") instead of crashing the turn
  or the call.
- **Deepgram (STT) / Rime (TTS) failures:** not yet explicitly handled —
  this is a known gap. An unhandled failure in either could currently
  interrupt or crash the session rather than degrading gracefully.