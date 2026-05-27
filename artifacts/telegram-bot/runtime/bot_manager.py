"""
BotManager — starts, stops, and monitors installed bots as isolated subprocesses.

Each bot runs as:
    python -m sources.<source_module>.main --bot-id <id> --token <encrypted_token>

The manager:
- Spawns one subprocess per bot_id
- Tracks PIDs in memory + DB (Bot.pid)
- Provides heartbeat checks
- Restarts crashed bots (with back-off)
- Exposes start_bot / stop_bot / restart_bot / status API
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select, update

from database.models import Bot
from database.session import async_session_maker
from runtime.crypto import decrypt_token

logger = logging.getLogger(__name__)

# Root of the telegram-bot package (where sources/ lives)
_BASE_DIR = Path(__file__).resolve().parent.parent

# Maximum restart attempts before giving up
_MAX_RESTARTS   = 5
# Back-off seconds between restarts (doubles each time)
_BACKOFF_BASE   = 5


@dataclass
class _BotProcess:
    bot_id:    int
    source_id: int
    proc:      asyncio.subprocess.Process
    restarts:  int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)


class BotManager:
    """Singleton — use `get_manager()` to obtain the instance."""

    def __init__(self) -> None:
        self._procs: dict[int, _BotProcess] = {}   # bot_id → _BotProcess
        self._lock  = asyncio.Lock()
        self._watcher_task: asyncio.Task | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def start_bot(self, bot_id: int) -> bool:
        """
        Load bot record from DB, decrypt token, spawn subprocess.
        Returns True on success, False if already running.
        """
        async with self._lock:
            if bot_id in self._procs:
                logger.info("[manager] bot_id=%s already running (pid=%s)",
                            bot_id, self._procs[bot_id].proc.pid)
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
                logger.error("[manager] Failed to decrypt token for bot_id=%s: %s", bot_id, exc)
                return False

            proc = await self._spawn(bot_id, bot.source_id, token)
            if not proc:
                return False

            self._procs[bot_id] = _BotProcess(
                bot_id=bot_id, source_id=bot.source_id, proc=proc
            )
            await self._persist_status(bot_id, is_running=True, pid=proc.pid)
            logger.info("[manager] bot_id=%s started (pid=%s source=%s)",
                        bot_id, proc.pid, bot.source_id)
            return True

    async def stop_bot(self, bot_id: int) -> bool:
        """Send SIGTERM to the bot subprocess, wait up to 5s, then SIGKILL."""
        async with self._lock:
            entry = self._procs.pop(bot_id, None)
            if not entry:
                return False

            proc = entry.proc
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass

            await self._persist_status(bot_id, is_running=False, pid=None)
            logger.info("[manager] bot_id=%s stopped", bot_id)
            return True

    async def restart_bot(self, bot_id: int) -> bool:
        await self.stop_bot(bot_id)
        await asyncio.sleep(1)
        return await self.start_bot(bot_id)

    def is_running(self, bot_id: int) -> bool:
        entry = self._procs.get(bot_id)
        if not entry:
            return False
        return entry.proc.returncode is None

    def status(self, bot_id: int) -> dict:
        entry = self._procs.get(bot_id)
        if not entry:
            return {"running": False, "pid": None, "restarts": 0}
        return {
            "running":    entry.proc.returncode is None,
            "pid":        entry.proc.pid,
            "restarts":   entry.restarts,
            "started_at": entry.started_at.isoformat(),
        }

    def all_statuses(self) -> dict[int, dict]:
        return {bid: self.status(bid) for bid in self._procs}

    # ── Watcher — restarts crashed bots ──────────────────────────────────────

    async def start_watcher(self) -> None:
        if self._watcher_task and not self._watcher_task.done():
            return
        self._watcher_task = asyncio.create_task(self._watch_loop())
        logger.info("[manager] Watcher started.")

    async def _watch_loop(self) -> None:
        while True:
            await asyncio.sleep(10)
            crashed = [
                entry for entry in list(self._procs.values())
                if entry.proc.returncode is not None
            ]
            for entry in crashed:
                bid = entry.bot_id
                if entry.restarts >= _MAX_RESTARTS:
                    logger.error("[manager] bot_id=%s exceeded max restarts (%s) — giving up.",
                                 bid, _MAX_RESTARTS)
                    self._procs.pop(bid, None)
                    await self._persist_status(bid, is_running=False, pid=None)
                    continue

                backoff = _BACKOFF_BASE * (2 ** entry.restarts)
                logger.warning("[manager] bot_id=%s crashed (rc=%s) — restart #%s in %ss",
                               bid, entry.proc.returncode, entry.restarts + 1, backoff)
                await asyncio.sleep(backoff)

                async with self._lock:
                    self._procs.pop(bid, None)

                ok = await self.start_bot(bid)
                if ok and bid in self._procs:
                    self._procs[bid].restarts = entry.restarts + 1

    # ── Restore on platform restart ───────────────────────────────────────────

    async def restore_running_bots(self) -> None:
        """On SourceFarm startup, restart all bots that were running before."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Bot).where(Bot.is_running == True)  # noqa: E712
            )
            bots = result.scalars().all()

        logger.info("[manager] Restoring %s previously-running bots ...", len(bots))
        for bot in bots:
            await self.start_bot(bot.id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _spawn(
        self, bot_id: int, source_id: int, token: str
    ) -> asyncio.subprocess.Process | None:
        """Spawn the source as an isolated subprocess."""
        source_module = _source_module(source_id)
        if not source_module:
            logger.error("[manager] No source module for source_id=%s", source_id)
            return None

        cmd = [
            sys.executable, "-m", source_module,
            "--bot-id", str(bot_id),
            "--token",  token,
        ]
        env = {**os.environ, "PYTHONPATH": str(_BASE_DIR)}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(_BASE_DIR),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Drain output asynchronously so pipes don't block
            asyncio.create_task(_drain(proc, bot_id))
            return proc
        except Exception as exc:
            logger.error("[manager] Failed to spawn bot_id=%s: %s", bot_id, exc)
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


# ── Subprocess stdout/stderr drainer ─────────────────────────────────────────

async def _drain(proc: asyncio.subprocess.Process, bot_id: int) -> None:
    """Forward subprocess output to the parent logger."""
    sub_logger = logging.getLogger(f"bot.{bot_id}")
    async def _read(stream, level):
        while True:
            line = await stream.readline()
            if not line:
                break
            sub_logger.log(level, line.decode(errors="replace").rstrip())

    await asyncio.gather(
        _read(proc.stdout, logging.INFO),
        _read(proc.stderr, logging.WARNING),
    )


# ── Source ID → Python module path mapping ────────────────────────────────────

_SOURCE_MAP: dict[int, str] = {
    1: "sources.shield_suite.main",
}


def _source_module(source_id: int) -> str | None:
    return _SOURCE_MAP.get(source_id)


# ── Global singleton ──────────────────────────────────────────────────────────

_manager: BotManager | None = None


def get_manager() -> BotManager:
    global _manager
    if _manager is None:
        _manager = BotManager()
    return _manager
