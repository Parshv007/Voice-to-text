import asyncio
import itertools
import logging

from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext, WorkerOptions, cli, stt
from livekit.plugins import deepgram, rime, silero

try:
    from .models import OrderState
    from .order_logic import handle_user_utterance
except ImportError:
    from models import OrderState
    from order_logic import handle_user_utterance

load_dotenv()
logging.basicConfig(level=logging.INFO)

STT_TO_RIME_LANG = {
    "en": "eng",
    "hi": "hin",
}

STOP_WORDS = {"stop", "wait", "hold on", "ruko", "ruk", "ruk jao", "रुको"}


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
        self._current_language = "en"

    async def stt_node(self, audio, model_settings=None):
        async for event in Agent.default.stt_node(self, audio, model_settings):
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                detected = event.alternatives[0].language
                if detected:
                    detected = detected.split("-")[0]
                    if detected != self._current_language and detected in STT_TO_RIME_LANG:
                        self._current_language = detected
                        self.session.tts.update_options(
                            lang=STT_TO_RIME_LANG[detected]
                        )
            yield event

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = new_message.text_content
        if not text:
            return

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            self.session.interrupt()

        normalized = text.strip().lower()
        if normalized in STOP_WORDS or any(w in normalized for w in STOP_WORDS):
            return

        my_turn_id = next(self._turn_counter)
        self._current_turn_id = my_turn_id
        self._current_task = asyncio.create_task(
            self._process_turn(text, my_turn_id)
        )

    async def _process_turn(self, text: str, turn_id: int) -> None:
        try:
            async with self._order_lock:
                new_order, reply = await asyncio.to_thread(
                    handle_user_utterance, text, self.order, self._current_language
                )
                if turn_id != self._current_turn_id:
                    return
                self.order = new_order

                if turn_id != self._current_turn_id:
                    return
                try:
                    await self.session.say(reply, allow_interruptions=True)
                except Exception:
                    logging.exception("TTS failed for lang=%s reply=%r", self._current_language, reply)
        except asyncio.CancelledError:
            return


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logging.info(f"Participant connected: {participant.identity}")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3", language="multi"),
        tts=rime.TTS(
            model="coda",
            speaker="nadi",
            lang="eng",
        ),
    )

    await session.start(
        agent=OrderingAgent(),
        room=ctx.room,
    )

    await asyncio.sleep(0.5)  # let STT/VAD/interruption warmup settle before first TTS call

    await session.say(
        "Hi! What would you like to order today?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))