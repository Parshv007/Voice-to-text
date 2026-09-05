import asyncio
import itertools
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
        self._turn_counter = itertools.count()
        self._current_turn_id: int | None = None
        self._current_task: asyncio.Task | None = None
        self._order_lock = asyncio.Lock()

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = new_message.text_content
        if not text:
            return

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self.session.interrupt()

        my_turn_id = next(self._turn_counter)
        self._current_turn_id = my_turn_id
        self._current_task = asyncio.create_task(
            self._process_turn(text, my_turn_id)
        )

    async def _process_turn(self, text: str, turn_id: int) -> None:
        try:
            async with self._order_lock:
                new_order, reply = await asyncio.to_thread(
                    handle_user_utterance, text, self.order
                )
                if turn_id != self._current_turn_id:
                    return
                self.order = new_order

            if turn_id != self._current_turn_id:
                return
            await self.session.say(reply, allow_interruptions=True)
        except asyncio.CancelledError:
            return


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logging.info(f"Participant connected: {participant.identity}")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2-general",
            language="multi",
        ),
        tts=rime.TTS(
            model="coda",
            speaker="nadi",
            lang="hin",
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