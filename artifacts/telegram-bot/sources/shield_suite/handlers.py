"""
Shield Suite — all protection handlers.
Registered on the Dispatcher by ShieldSuitePlugin.
"""
from __future__ import annotations

import asyncio
import logging
import random
import string
from typing import TYPE_CHECKING

from aiogram import Bot, F, Router
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from sources.shield_suite.filters import (
    contains_link,
    is_forwarded,
    looks_like_spam,
    suspicious_account,
)
from sources.shield_suite.state import ShieldState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Captcha helpers ───────────────────────────────────────────────────────────

def _math_captcha() -> tuple[str, str]:
    """Returns (question_text, correct_answer)."""
    a, b = random.randint(1, 12), random.randint(1, 12)
    op   = random.choice(["+", "×"])
    ans  = a + b if op == "+" else a * b
    return f"{a} {op} {b} = ؟", str(ans)


def _decoy_answers(correct: str, n: int = 3) -> list[str]:
    """Generate n wrong numeric answers close to the correct one."""
    base  = int(correct)
    pool  = list(range(max(1, base - 5), base + 6))
    pool  = [x for x in pool if str(x) != correct]
    picks = random.sample(pool, min(n, len(pool)))
    return [str(p) for p in picks]


def _captcha_kb(correct: str, user_id: int) -> InlineKeyboardMarkup:
    options = [correct] + _decoy_answers(correct)
    random.shuffle(options)
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=opt,
                callback_data=f"cap_{user_id}_{'ok' if opt == correct else 'no'}_{opt}",
            )
            for opt in options
        ]]
    )


# ── Router factory ─────────────────────────────────────────────────────────────

def build_router(state: ShieldState, config: dict, bot_id: int) -> Router:
    router = Router(name=f"shield_{bot_id}")

    # ── New member — captcha gate ─────────────────────────────────────────────

    @router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
    async def on_new_member(event: ChatMemberUpdated, bot: Bot) -> None:
        user    = event.new_chat_member.user
        chat_id = event.chat.id

        # Raid detection
        raid_threshold = config.get("raid_threshold", 10)
        if state.raid_join(chat_id, raid_threshold):
            if not state.is_raid_locked(chat_id):
                state.set_raid_lock(chat_id, True)
                try:
                    await bot.set_chat_permissions(
                        chat_id,
                        ChatPermissions(can_send_messages=False),
                    )
                    await bot.send_message(
                        chat_id,
                        "⚠️ <b>تم رصد هجوم ريد!</b>\n"
                        "تم تجميد المجموعة مؤقتاً لحماية الأعضاء.\n"
                        "سيتم رفع التجميد خلال دقيقتين تلقائياً.",
                    )
                    asyncio.create_task(_unlock_raid(bot, chat_id, state, delay=120))
                    logger.warning("[shield bot_id=%s] Raid detected in chat=%s", bot_id, chat_id)
                except Exception as exc:
                    logger.error("[shield] Raid lock failed: %s", exc)
            return

        if user.is_bot:
            return

        if not config.get("captcha_enabled", True):
            return

        # Restrict user until captcha solved
        try:
            await bot.restrict_chat_member(
                chat_id, user.id,
                ChatPermissions(can_send_messages=False),
            )
        except Exception:
            pass

        question, answer = _math_captcha()
        timeout = config.get("captcha_timeout", 60)

        try:
            msg = await bot.send_message(
                chat_id,
                f"👋 مرحباً <b>{user.first_name}</b>!\n\n"
                f"لإثبات أنك لست بوتاً، احسب:\n\n"
                f"<b>{question}</b>\n\n"
                f"⏳ لديك <b>{timeout}</b> ثانية للإجابة.",
                reply_markup=_captcha_kb(answer, user.id),
            )
            state.set_captcha(chat_id, user.id, msg.message_id)
            asyncio.create_task(
                _captcha_timeout(bot, chat_id, user.id, msg.message_id, state, timeout)
            )
        except Exception as exc:
            logger.error("[shield] Captcha send failed: %s", exc)

    # ── Captcha answer callback ───────────────────────────────────────────────

    @router.callback_query(F.data.startswith("cap_"))
    async def on_captcha_answer(cb: CallbackQuery, bot: Bot) -> None:
        # cap_{user_id}_{ok|no}_{value}
        parts = cb.data.split("_", 3)
        if len(parts) < 3:
            return

        target_uid = int(parts[1])
        verdict    = parts[2]    # "ok" or "no"
        chat_id    = cb.message.chat.id

        # Only the challenged user can answer
        if cb.from_user.id != target_uid:
            await cb.answer("هذا السؤال ليس لك!", show_alert=True)
            return

        msg_id = state.pop_captcha(chat_id, target_uid)
        if msg_id is None:
            await cb.answer()
            return

        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

        if verdict == "ok":
            try:
                await bot.restrict_chat_member(
                    chat_id, target_uid,
                    ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                    ),
                )
                await cb.answer("✅ تم التحقق! مرحباً بك.", show_alert=False)
                logger.info("[shield bot_id=%s] Captcha passed: user=%s chat=%s",
                            bot_id, target_uid, chat_id)
            except Exception as exc:
                logger.error("[shield] Unrestrict failed: %s", exc)
        else:
            try:
                await bot.ban_chat_member(chat_id, target_uid)
                await cb.answer("❌ إجابة خاطئة — تم طردك.", show_alert=True)
                logger.info("[shield bot_id=%s] Captcha failed — banned: user=%s chat=%s",
                            bot_id, target_uid, chat_id)
            except Exception as exc:
                logger.error("[shield] Ban after captcha fail: %s", exc)

    # ── Message filter ────────────────────────────────────────────────────────

    @router.message(F.chat.type.in_({"group", "supergroup"}))
    async def on_group_message(message: Message, bot: Bot) -> None:
        if not message.from_user:
            return

        user    = message.from_user
        chat_id = message.chat.id
        uid     = user.id
        text    = message.text or message.caption or ""

        # Skip admins
        try:
            member = await bot.get_chat_member(chat_id, uid)
            if member.status in ("administrator", "creator"):
                return
        except Exception:
            pass

        # Flood check
        threshold = config.get("flood_threshold", 5)
        if state.flood_count(chat_id, uid, threshold):
            await _warn_or_ban(message, bot, state, config, bot_id,
                               reason="فلود (رسائل متكررة بسرعة)")
            return

        # Captcha still pending — block their messages
        if state.has_captcha(chat_id, uid):
            try:
                await message.delete()
            except Exception:
                pass
            return

        # Link filter
        if config.get("block_links", True) and contains_link(text):
            await _warn_or_ban(message, bot, state, config, bot_id,
                               reason="روابط خارجية")
            return

        # Forwarded message filter
        if config.get("block_forwarded", False) and is_forwarded(message):
            await _warn_or_ban(message, bot, state, config, bot_id,
                               reason="رسائل مُعاد توجيهها")
            return

        # Spam keyword filter
        if looks_like_spam(text):
            await _warn_or_ban(message, bot, state, config, bot_id,
                               reason="محتوى مشبوه (سبام)")
            return

    return router


# ── Shared action helpers ─────────────────────────────────────────────────────

async def _warn_or_ban(
    message: Message,
    bot: Bot,
    state: ShieldState,
    config: dict,
    bot_id: int,
    reason: str,
) -> None:
    uid     = message.from_user.id
    chat_id = message.chat.id
    limit   = config.get("warn_limit", 3)

    try:
        await message.delete()
    except Exception:
        pass

    warns = state.add_warn(chat_id, uid)
    remaining = limit - warns

    if warns >= limit:
        state.reset_warns(chat_id, uid)
        try:
            await bot.ban_chat_member(chat_id, uid)
            await bot.send_message(
                chat_id,
                f"🚫 تم حظر <a href='tg://user?id={uid}'>المستخدم</a> "
                f"بسبب: <b>{reason}</b>\n"
                f"({warns}/{limit} تحذيرات مستنفدة)",
            )
            logger.info("[shield bot_id=%s] Banned user=%s chat=%s reason=%s",
                        bot_id, uid, chat_id, reason)
        except Exception as exc:
            logger.error("[shield] Ban failed: %s", exc)
    else:
        try:
            warn_msg = await bot.send_message(
                chat_id,
                f"⚠️ تحذير {warns}/{limit} لـ <a href='tg://user?id={uid}'>هذا المستخدم</a>\n"
                f"السبب: <b>{reason}</b>\n"
                f"{'سيتم الحظر عند التحذير القادم!' if remaining == 1 else f'متبقٍ {remaining} تحذيرات.'}",
            )
            # Auto-delete warning after 15 seconds
            asyncio.create_task(_delete_after(bot, chat_id, warn_msg.message_id, 15))
        except Exception as exc:
            logger.error("[shield] Warn message failed: %s", exc)


async def _captcha_timeout(
    bot: Bot,
    chat_id: int,
    user_id: int,
    msg_id: int,
    state: ShieldState,
    timeout: int,
) -> None:
    await asyncio.sleep(timeout)
    if state.pop_captcha(chat_id, user_id) is None:
        return   # Already answered
    try:
        await bot.delete_message(chat_id, msg_id)
        await bot.ban_chat_member(chat_id, user_id)
        logger.info("[shield] Captcha timeout — banned: user=%s chat=%s", user_id, chat_id)
    except Exception as exc:
        logger.error("[shield] Captcha timeout action failed: %s", exc)


async def _unlock_raid(
    bot: Bot, chat_id: int, state: ShieldState, delay: int
) -> None:
    await asyncio.sleep(delay)
    state.set_raid_lock(chat_id, False)
    try:
        await bot.set_chat_permissions(
            chat_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await bot.send_message(
            chat_id,
            "✅ <b>انتهى وضع الطوارئ.</b>\n"
            "تم رفع تجميد المجموعة. البوت يواصل المراقبة.",
        )
    except Exception as exc:
        logger.error("[shield] Unlock raid failed: %s", exc)


async def _delete_after(bot: Bot, chat_id: int, msg_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass
