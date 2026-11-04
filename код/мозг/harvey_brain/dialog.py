"""Диалог: сон/бодрствование, слово пробуждения, быстрые команды или LLM, события головы."""
from .commands import quick_reply, wants_action
from .reply import Reply
from .wake import normalize, split_wake

EVENT_REPLIES = {
    "lifted": Reply("Ой! Поставь меня, пожалуйста.", "surprised"),
    "docked": Reply("Ммм, зарядка.", "happy"),
    "bat_low": Reply("Я устал, пойду заряжаться.", "tired"),
}
EVENT_GAP_S = 20.0


class Dialog:
    def __init__(self, llm, follow_s: float = 8.0):
        self.llm, self.follow_s = llm, follow_s
        self._awake_until = float("-inf")
        self._last_event: dict[str, float] = {}

    def awake(self, now: float) -> bool:
        return now < self._awake_until

    def on_text(self, text: str, now: float) -> Reply | None:
        woke, rest = split_wake(text)
        if not woke and not self.awake(now):
            return None
        if not rest and not woke:
            return None
        reply = self._answer(rest) if rest or not woke else Reply("Да?", "curious")
        self._awake_until = now + self.follow_s
        return reply

    def _answer(self, rest: str) -> Reply:
        quick = quick_reply(rest)
        if quick:
            return quick
        reply = self.llm.ask(rest)
        if not wants_action(rest):
            reply.goal = None
        return reply

    def on_head(self, msg: dict, now: float) -> Reply | None:
        name = msg.get("ev") if msg.get("t") == "ev" else None
        reply = EVENT_REPLIES.get(name)
        if reply is None or now - self._last_event.get(name, float("-inf")) < EVENT_GAP_S:
            return None
        self._last_event[name] = now
        return reply
