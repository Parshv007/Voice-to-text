import logging

from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, rime, silero

load_dotenv()
logging.basicConfig(level=logging.INFO)


class EchoAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a simple echo test agent. Repeat back exactly what the "
                "user said, prefixed with 'You said: '. Do not add anything else."
            ),
        )


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logging.info(f"Participant connected: {participant.identity}")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        tts=rime.TTS(
            model="mistv2",
            speaker="marsh",  # Replace with your desired Rime voice
        ),
    )

    await session.start(
        agent=EchoAgent(),
        room=ctx.room,
    )

    await session.say("Pipeline connected. Say something to test echo.", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))