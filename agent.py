import logging

from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, rime, silero

try:
    from .models import OrderState
    from .order_logic import handle_user_utterance
except ImportError:
    from models import OrderState
    from order_logic import handle_user_utterance

load_dotenv()
logging.basicConfig(level=logging.INFO)


class OrderingAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a voice ordering assistant.",
        )
        self.order = OrderState()

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = new_message.text_content
        if not text:
            return

        self.order, reply = handle_user_utterance(text, self.order)
        await self.session.say(reply, allow_interruptions=True)


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logging.info(f"Participant connected: {participant.identity}")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3", language="multi"),
        tts=rime.TTS(
            model="mistv2",
            speaker="marsh",
        ),
    )

    await session.start(
        agent=OrderingAgent(),
        room=ctx.room,
    )

    await session.say(
        "Hi, welcome! What can I get started for you today?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))