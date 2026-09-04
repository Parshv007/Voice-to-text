import asyncio
import logging
from dotenv import load_dotenv

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, rime, silero

load_dotenv()
logging.basicConfig(level=logging.INFO)

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logging.info(f"Participant connected: {participant.identity}")

    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        tts=rime.TTS(
            model="v1",
            speaker="marsh"  # Replace with your desired Rime voice
        ),
    )

    @agent.on("user_speech_committed")
    def on_user_speech(msg):
        text = msg.content
        if text.strip():
            logging.info(f"Transcribed: {text}")
            asyncio.create_task(agent.say(f"You said: {text}", allow_interruptions=True))

    agent.start(ctx.room, participant)
    await agent.say("Pipeline connected. Say something to test echo.", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))