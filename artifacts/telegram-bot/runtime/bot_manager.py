"""
BotManager — manages installed bots as isolated subprocesses.

Each bot runs in its own Python process via runtime/bot_runner.py.
This isolates crashes, memory leaks, and blocking calls from the main bot.

Lifecycle:
    start_bot()   → spawn subprocess via asyncio.create_subprocess_exec
    stop_bot()    → SIGTERM → wait 5s → SIGKILL
    restart_bot() → stop + start
    Watcher loop  → detects exited processes, restarts with back-off
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update

from database.models import Bot
from database.session import async_session_maker
from runtime.crypto import decrypt_token

logger = logging.getLogger(__name__)

_BASE_DIR     = Path(__file__).resolve().parent.parent
_RUNNER       = _BASE_DIR / "runtime" / "bot_runner.py"
_MAX_RESTARTS = 5
_BACKOFF_BASE = 5


@dataclass
class _BotEntry:
    bot_id:     int
    source_id:  int
    proc:       asyncio.subprocess.Process
    restarts:   int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)


async def _stream_logs(bot_id: int, stream: asyncio.StreamReader) -> None:
    """Forward subprocess stdout/stderr to the main process logger."""
    log = logging.getLogger(f"bot.{bot_id}")
    try:
        async for raw in stream:
            line = raw.decode(errors="replace").rstrip()
            if line:
                log.info(line)
    except Exception:
        pass


class BotManager:
    """Singleton — use `get_manager()` to obtain the instance."""

    def __init__(self) -> None:
        self._entries: dict[int, _BotEntry] = {}
        self._lock    = asyncio.Lock()
        self._watcher: asyncio.Task | None  = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def start_bot(self, bot_id: int) -> bool:
        async with self._lock:
            entry = self._entries.get(bot_id)
            if entry and entry.proc.returncode is None:
                logger.info("[manager] bot_id=%s already running", bot_id)
                return False

            bot = await self._load_bot(bot_id)
            if not bot:
                logger.error("[manager] bot_id=%s not found in DB", bot_id)
                return False
            if not bot.token_encrypted:
                logger.error("[manager] bot_id=%s has no encrypted token", bot_id)
                return False

            try:
                token = decrypt_token(bot.token_encrypted)
            except Exception as exc:
                logger.error("[manager] Cannot decrypt token for bot_id=%s: %s", bot_id, exc)
                return False

            proc = await self._spawn(bot_id, bot.source_id, token)
            if not proc:
                return False

            self._entries[bot_id] = _BotEntry(
                bot_id=bot_id, source_id=bot.source_id, proc=proc
            )
            await self._persist_status(bot_id, is_running=True, pid=proc.pid)
            logger.info("[manager] bot_id=%s started (pid=%s source=%s)", bot_id, proc.pid, bot.source_id)
            return True

    async def stop_bot(self, bot_id: int) -> bool:
        async with self._lock:
            entry = self._entries.pop(bot_id, None)
            if not entry:
                return False

            proc = entry.proc
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("[manager] bot_id=%s did not exit — sending SIGKILL", bot_id)
                    proc.kill()
                    await proc.wait()

            await self._persist_status(bot_id, is_running=False, pid=None)
            logger.info("[manager] bot_id=%s stopped (exit=%s)", bot_id, proc.returncode)
            return True

    async def restart_bot(self, bot_id: int) -> bool:
        await self.stop_bot(bot_id)
        await asyncio.sleep(1)
        return await self.start_bot(bot_id)

    def is_running(self, bot_id: int) -> bool:
        entry = self._entries.get(bot_id)
        return bool(entry and entry.proc.returncode is None)

    def status(self, bot_id: int) -> dict:
        entry = self._entries.get(bot_id)
        if not entry:
            return {"running": False, "pid": None, "restarts": 0}
        return {
            "running":    entry.proc.returncode is None,
            "pid":        entry.proc.pid,
            "restarts":   entry.restarts,
            "started_at": entry.started_at.isoformat(),
            "exit_code":  entry.proc.returncode,
        }

    def all_statuses(self) -> dict[int, dict]:
        return {bid: self.status(bid) for bid in self._entries}

    # ── Watcher ───────────────────────────────────────────────────────────────

    async def start_watcher(self) -> None:
        if self._watcher and not self._watcher.done():
            return
        self._watcher = asyncio.create_task(self._watch_loop(), name="bot_manager_watcher")
        logger.info("[manager] Watcher started.")

    async def _watch_loop(self) -> None:
        while True:
            await asyncio.sleep(10)
            crashed = [
                e for e in list(self._entries.values())
                if e.proc.returncode is not None
            ]
            for entry in crashed:
                bid = entry.bot_id
                if entry.restarts >= _MAX_RESTARTS:
                    logger.error(
                        "[manager] bot_id=%s exceeded max restarts (%s) — giving up.",
                        bid, _MAX_RESTARTS,
                    )
                    self._entries.pop(bid, None)
                    await self._persist_status(bid, is_running=False, pid=None)
                    continue

                backoff = _BACKOFF_BASE * (2 ** entry.restarts)
                logger.warning(
                    "[manager] bot_id=%s exited (rc=%s) — restart #%s in %ss",
                    bid, entry.proc.returncode, entry.restarts + 1, backoff,
                )
                await asyncio.sleep(backoff)

                async with self._lock:
                    self._entries.pop(bid, None)

                ok = await self.start_bot(bid)
                if ok and bid in self._entries:
                    self._entries[bid].restarts = entry.restarts + 1

    # ── Restore on platform restart ───────────────────────────────────────────

    async def restore_running_bots(self) -> None:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Bot).where(Bot.is_running == True)  # noqa: E712
            )
            bots = result.scalars().all()

        logger.info("[manager] Restoring %s previously-running bot(s) ...", len(bots))
        for bot in bots:
            await self.start_bot(bot.id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _spawn(
        self, bot_id: int, source_id: int, token: str
    ) -> asyncio.subprocess.Process | None:
        env = {
            **os.environ,
            "SF_BOT_ID":    str(bot_id),
            "SF_SOURCE_ID": str(source_id),
            "SF_BOT_TOKEN": token,
        }
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(_RUNNER),
                env=env,
                cwd=str(_BASE_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            asyncio.create_task(
                _stream_logs(bot_id, proc.stdout),
                name=f"bot_logs_{bot_id}",
            )
            return proc
        except Exception as exc:
            logger.error("[manager] Failed to spawn subprocess for bot_id=%s: %s", bot_id, exc)
            return None

    @staticmethod
    async def _load_bot(bot_id: int) -> Bot | None:
        async with async_session_maker() as session:
            result = await session.execute(select(Bot).where(Bot.id == bot_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def _persist_status(bot_id: int, is_running: bool, pid: int | None) -> None:
        async with async_session_maker() as session:
            await session.execute(
                update(Bot)
                .where(Bot.id == bot_id)
                .values(is_running=is_running, pid=pid)
            )
            await session.commit()


# ── Global singleton ──────────────────────────────────────────────────────────

_manager: BotManager | None = None


def get_manager() -> BotManager:
    global _manager
    if _manager is None:
        _manager = BotManager()
    return _manager
