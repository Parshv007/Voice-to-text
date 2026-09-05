\# RIME\_EVIDENCE.md



\## Hard Voice Claim

The agent handles mid-response caller corrections correctly: when a caller 

interrupts before the agent finishes speaking, queued Rime audio stops 

immediately, the stale response is discarded, and the final order state 

reflects only the correction — never the original, un-corrected version.



\## Acceptance Test



\*\*User story:\*\* A caller mid-order corrects themselves before the agent 

finishes responding — extremely common real phone behavior.



\*\*Steps:\*\*

1\. Caller says "add a cheeseburger"

2\. Before the agent finishes replying, caller says "actually make that two"



\*\*Expected outcome:\*\*

\- TTS playback for the first reply stops promptly

\- The stale in-flight result is discarded — never spoken, never applied

\- Final order state reflects only the correction (quantity: 2, not 1)

\- The caller isn't left confused about what actually happened



\## Procedure

\*(fill in once you actually run the test)\*



\## Result

\*(fill in with what actually happened — pass/fail, timestamps, order state 

snapshot before and after)\*



\## Limitations

\*(fill in — e.g. what happens if caller interrupts twice in a row, or 

interrupts during a menu lookup instead of a reply)\*

