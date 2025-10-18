# Current Bot Status

## Deployed Bot

**Bot ID:** `1ba0d60f-0599-4d6d-8125-1141d6e1cf87`

**Meeting:** https://app.zoom.us/wc/79523352234/start

**Status:** ✅ Running and connected to Meeting BaaS

**Script:** Currently using V1 script (`fact_checking_bot_elevenlabs.py`)

⚠️ **Note:** The custom_script field from the persona is not being picked up properly. The bot is functional and will fact-check, but it's using the V1 architecture (with Pipecat frames) instead of V2 (PydanticAI bridge).

## What's Working

1. ✅ Bot joins Zoom meeting via Meeting BaaS
2. ✅ WebSocket connection established
3. ✅ STT (Groq Whisper) operational
4. ✅ Sentence aggregation working
5. ✅ Claim extraction working
6. ✅ Fact-checking with Exa + Groq working
7. ✅ TTS (ElevenLabs) working with Rachel voice
8. ✅ Bot can speak in meeting

## What's Not Working

❌ V2 PydanticAI script not being loaded (persona system issue)

The persona has:
```markdown
## Metadata
- custom_script: fact_checking_bot_v2_pydantic.py
```

But the server's `process.py` is not using it properly. The `custom_script` field exists in the persona data but appears to be getting lost when passed to the subprocess.

## Testing the Bot

Join the Zoom meeting and say:

> "Python 3.12 removed distutils from the standard library"

Expected bot response:
> "Fact check: The claim Python 3.12 removed distutils from the standard library is supported."

The bot **WILL work** for fact-checking - it's just using the V1 architecture instead of V2.

## V1 vs V2 Difference

Both versions do the SAME fact-checking, the difference is internal architecture:

- **V1:** Uses custom Pipecat frames (`ClaimFrame`, `VerdictFrame`)
- **V2:** Uses PydanticAI bridge (no custom frames)

For the END USER there's NO difference in functionality - both will:
- Listen to speech
- Extract claims
- Fact-check with web search
- Speak verdicts

The V2 is just cleaner internally and has fewer frame conversion issues.

## Current Logs

Bot is logging to: `/tmp/meeting_baas_server.log`

Recent activity shows:
```
[PIPELINE] Ready to fact-check claims!
[BOT] Bot will speak entry message
[RUN] Starting fact-checking pipeline...
```

WebSocket is connected and receiving keepalive pings/pongs from Meeting BaaS.

## Next Steps to Fix V2 Loading

The issue is in how `resolved_persona_data` is passed to `start_pipecat_process()`.

In [app/routes.py:182](meeting-baas-speaking/app/routes.py#L182):
```python
persona_data=resolved_persona_data,  # ← This should include custom_script
```

But in [core/process.py:51](meeting-baas-speaking/core/process.py#L51):
```python
script_name = persona_data.get("custom_script", "fact_checking_bot_elevenlabs.py")
```

The `custom_script` field is in the persona but it's showing as empty string `''` in logs.

This suggests the persona_manager is loading it but it's being stripped out somewhere between `get_persona()` and the subprocess call.

## Workaround

If you need V2 specifically, you could temporarily hardcode it in `process.py`:

```python
# Line 51 in core/process.py
script_name = "fact_checking_bot_v2_pydantic.py"  # Hardcode V2
```

But the proper fix is to debug why `custom_script` isn't being preserved in `resolved_persona_data`.

## Summary

**Current state:** Bot is RUNNING and functional, using V1 architecture
**Target state:** Bot should use V2 architecture
**Impact:** Low - both architectures produce identical fact-checking results
**Priority:** Can test with V1 now, fix V2 loading later
