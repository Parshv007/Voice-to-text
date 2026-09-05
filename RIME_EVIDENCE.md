# RIME_EVIDENCE.md

## Overview

This document covers three hard voice claims for the voice ordering agent:
1. Mid-response caller correction handling (interruption + conversation continuity)
2. Automatic language switching between Hindi and English (including Hinglish)
3. Immediate silence on explicit stop commands ("stop" / "ruko")

Rime provides the primary spoken output throughout. Model/speaker/language
details are in README.md.

---

## Claim 1: Mid-Response Caller Corrections

The agent handles mid-response caller corrections correctly: when a caller
interrupts before the agent finishes speaking, queued Rime audio stops
immediately, the stale response is discarded, and the final order state
reflects only the correction — never the original, un-corrected version.

### Acceptance Test

**User story:** A caller mid-order corrects themselves before the agent
finishes responding — extremely common real phone behavior.

**Steps:**
1. Caller says "add a cheeseburger"
2. Before the agent finishes replying, caller says "actually make that two"

**Expected outcome:**
- TTS playback for the first reply stops promptly
- The stale in-flight result is discarded — never spoken, never applied
- Final order state reflects only the correction (quantity: 2, not 1)
- The caller isn't left confused about what actually happened

### Procedure
*(fill in — e.g. "Ran locally via LiveKit Playground, agent.py in dev mode,
[date/time]")*

### Result
*(fill in — pass/fail, order state snapshot before and after, any
timestamps or terminal log excerpts showing turn cancellation)*

### Limitations
*(fill in — e.g. behavior with two rapid interruptions in a row, or an
interruption during a menu/total lookup instead of a reply)*

---

## Claim 2: Automatic Language Switching (Hindi / English / Hinglish)

The agent detects the caller's spoken language per turn (via Deepgram
nova-3 in multilingual mode) and replies in that same language — rather
than guessing from text alone — including switching TTS output language
mid-call to match.

### Acceptance Test

**User story:** A caller may speak Hindi, English, or a Hindi-English mix,
and may switch between them across turns without warning.

**Steps:**
1. Caller says an order line in English (e.g. "add a cheeseburger")
2. Caller then says the next line in Hindi (e.g. "ek cold drink bhi de do")
3. Caller then says a line mixing both (Hinglish)

**Expected outcome:**
- Each reply is spoken in the same language the caller just used
- The order is correctly understood and updated regardless of language
- No language "sticks" incorrectly from a previous turn

### Procedure
*(fill in — describe exact phrases spoken for each of the 3 steps)*

### Result
*(fill in — pass/fail per step, note which language each reply actually
came back in)*

### Limitations
*(fill in — e.g. accuracy on heavily code-switched sentences, languages
outside Hindi/English, or short single-word utterances that are ambiguous
to detect)*

---

## Claim 3: Immediate Silence on Stop Command

Saying "stop," "wait," or "ruko" while the agent is speaking or processing
immediately cancels in-flight work and produces silence — not a new
LLM-generated reply. This is a deterministic keyword-based kill-switch,
not an LLM judgment call, chosen to guarantee zero added latency.

### Acceptance Test

**User story:** A caller wants the agent to stop talking right now, without
waiting for a generated response acknowledging the stop.

**Steps:**
1. Caller says "add two burgers and a large fries"
2. While the agent is still speaking its response, caller says "stop" (or
   "ruko")

**Expected outcome:**
- Any queued/playing Rime audio stops immediately
- No further reply is generated or spoken for that turn
- The order state remains whatever it was before the "stop" — the stop
  itself does not modify the order

### Procedure
*(fill in — exact phrasing used, timing of the interrupt)*

### Result
*(fill in — pass/fail, and whether audio actually cut immediately or with
a noticeable delay)*

### Limitations
*(fill in — this is a fixed keyword list, not semantic understanding: only
covers stop/wait/ruko and close variants, not all possible phrasings a
caller might use to ask the agent to stop)*