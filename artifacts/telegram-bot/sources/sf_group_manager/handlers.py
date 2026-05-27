"""SF Group Manager — all handlers."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiogram import Bot, F, Router
from aiogram.filters import ChatMemberUpdatedFilter, Command, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    Message,
)

from sources.sf_group_manager.state import GroupManagerState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def _mention(user) -> str:
    return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'


async def _delete_after(bot: Bot, chat_id: int, msg_id: int, delay: int = 10) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


# ── Router factory ─────────────────────────────────────────────────────────────

def build_router(state: GroupManagerState, config: dict, bot_id: int) -> Router:
    router = Router(name=f"sfgm_{bot_id}")

    # ── Welcome on new member ─────────────────────────────────────────────────

    @router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
    async def on_join(event: ChatMemberUpdated, bot: Bot) -> None:
        if not config.get("welcome_enabled", True):
            return
        user = event.new_chat_member.user
        if user.is_bot:
            return
        chat = event.chat
        text = config.get("welcome_text", "👋 مرحباً {name} في {chat}!")
        text = text.replace("{name}", _mention(user)).replace("{chat}", f"<b>{chat.title}</b>")
        try:
            await bot.send_message(chat.id, text, parse_mode="HTML")
        except Exception as exc:
            logger.error("[sfgm bot_id=%s] Welcome send failed: %s", bot_id, exc)

    # ── Delete service messages (join/leave) ──────────────────────────────────

    @router.message(F.content_type.in_({"new_chat_members", "left_chat_member"}))
    async def delete_service(message: Message, bot: Bot) -> None:
        if config.get("delete_service_msgs", True):
            try:
                await message.delete()
            except Exception:
                pass

    # ── /ban ─────────────────────────────────────────────────────────────────

    @router.message(Command("ban"))
    async def cmd_ban(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد حظره.")
            return

        reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "لم يُذكر"
        try:
            await bot.ban_chat_member(message.chat.id, target.from_user.id)
            state.reset_warns(message.chat.id, target.from_user.id)
            await message.answer(
                f"🚫 تم حظر {_mention(target.from_user)}\n"
                f"السبب: <b>{reason}</b>",
                parse_mode="HTML",
            )
            logger.info("[sfgm bot_id=%s] Banned user=%s", bot_id, target.from_user.id)
        except Exception as exc:
            await message.reply(f"⚠️ فشل الحظر: {exc}")

    # ── /unban ────────────────────────────────────────────────────────────────

    @router.message(Command("unban"))
    async def cmd_unban(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد رفع حظره.")
            return

        try:
            await bot.unban_chat_member(message.chat.id, target.from_user.id, only_if_banned=True)
            await message.answer(
                f"✅ تم رفع الحظر عن {_mention(target.from_user)}",
                parse_mode="HTML",
            )
        except Exception as exc:
            await message.reply(f"⚠️ فشل رفع الحظر: {exc}")

    # ── /kick ─────────────────────────────────────────────────────────────────

    @router.message(Command("kick"))
    async def cmd_kick(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد طرده.")
            return

        try:
            await bot.ban_chat_member(message.chat.id, target.from_user.id)
            await bot.unban_chat_member(message.chat.id, target.from_user.id)
            await message.answer(
                f"👟 تم طرد {_mention(target.from_user)} — يمكنه الانضمام مجدداً.",
                parse_mode="HTML",
            )
        except Exception as exc:
            await message.reply(f"⚠️ فشل الطرد: {exc}")

    # ── /mute ─────────────────────────────────────────────────────────────────

    @router.message(Command("mute"))
    async def cmd_mute(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد تكميمه.")
            return

        try:
            await bot.restrict_chat_member(
                message.chat.id, target.from_user.id,
                ChatPermissions(can_send_messages=False),
            )
            await message.answer(
                f"🔇 تم تكميم {_mention(target.from_user)}",
                parse_mode="HTML",
            )
        except Exception as exc:
            await message.reply(f"⚠️ فشل التكميم: {exc}")

    # ── /unmute ───────────────────────────────────────────────────────────────

    @router.message(Command("unmute"))
    async def cmd_unmute(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد رفع التكميم عنه.")
            return

        try:
            await bot.restrict_chat_member(
                message.chat.id, target.from_user.id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            await message.answer(
                f"🔊 تم رفع التكميم عن {_mention(target.from_user)}",
                parse_mode="HTML",
            )
        except Exception as exc:
            await message.reply(f"⚠️ فشل رفع التكميم: {exc}")

    # ── /warn ─────────────────────────────────────────────────────────────────

    @router.message(Command("warn"))
    async def cmd_warn(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد تحذيره.")
            return

        limit  = config.get("warn_limit", 3)
        reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "لم يُذكر"
        warns  = state.add_warn(message.chat.id, target.from_user.id)

        if warns >= limit:
            state.reset_warns(message.chat.id, target.from_user.id)
            try:
                await bot.ban_chat_member(message.chat.id, target.from_user.id)
                await message.answer(
                    f"🚫 تم حظر {_mention(target.from_user)} بعد {limit} تحذيرات.\n"
                    f"آخر سبب: <b>{reason}</b>",
                    parse_mode="HTML",
                )
            except Exception as exc:
                await message.reply(f"⚠️ فشل الحظر بعد التحذيرات: {exc}")
        else:
            remaining = limit - warns
            await message.answer(
                f"⚠️ تحذير {warns}/{limit} لـ {_mention(target.from_user)}\n"
                f"السبب: <b>{reason}</b>\n"
                f"{'⛔ التحذير القادم = حظر دائم!' if remaining == 1 else f'متبقٍ {remaining} تحذير/ات.'}",
                parse_mode="HTML",
            )
        logger.info("[sfgm bot_id=%s] Warned user=%s warns=%s/%s", bot_id, target.from_user.id, warns, limit)

    # ── /unwarn ───────────────────────────────────────────────────────────────

    @router.message(Command("unwarn"))
    async def cmd_unwarn(message: Message, bot: Bot) -> None:
        if config.get("admin_only_cmds", True):
            if not await _is_admin(bot, message.chat.id, message.from_user.id):
                await message.reply("❌ هذا الأمر للمشرفين فقط.")
                return

        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم المراد إلغاء تحذيره.")
            return

        warns = state.remove_warn(message.chat.id, target.from_user.id)
        limit = config.get("warn_limit", 3)
        await message.answer(
            f"✅ تم إلغاء تحذير عن {_mention(target.from_user)}\n"
            f"تحذيراته الآن: <b>{warns}/{limit}</b>",
            parse_mode="HTML",
        )

    # ── /warns ────────────────────────────────────────────────────────────────

    @router.message(Command("warns"))
    async def cmd_warns(message: Message) -> None:
        target = message.reply_to_message
        if not target:
            await message.reply("↩️ ردّ على رسالة المستخدم للاستعلام عن تحذيراته.")
            return

        warns = state.get_warns(message.chat.id, target.from_user.id)
        limit = config.get("warn_limit", 3)
        await message.answer(
            f"📋 تحذيرات {_mention(target.from_user)}: <b>{warns}/{limit}</b>",
            parse_mode="HTML",
        )

    # ── /rules ────────────────────────────────────────────────────────────────

    @router.message(Command("rules"))
    async def cmd_rules(message: Message) -> None:
        rules = config.get("rules_text", "📋 لا توجد قواعد محددة بعد.")
        await message.answer(
            f"📋 <b>قواعد المجموعة:</b>\n\n{rules}",
            parse_mode="HTML",
        )

    # ── /admins ───────────────────────────────────────────────────────────────

    @router.message(Command("admins"))
    async def cmd_admins(message: Message, bot: Bot) -> None:
        try:
            admins = await bot.get_chat_administrators(message.chat.id)
            lines  = ["👮 <b>مشرفو المجموعة:</b>\n"]
            for a in admins:
                if a.user.is_bot:
                    continue
                icon = "👑" if a.status == "creator" else "🔰"
                name = a.user.full_name
                lines.append(f"{icon} <a href='tg://user?id={a.user.id}'>{name}</a>")
            await message.answer("\n".join(lines), parse_mode="HTML")
        except Exception as exc:
            await message.reply(f"⚠️ تعذّر جلب قائمة المشرفين: {exc}")

    # ── /id ───────────────────────────────────────────────────────────────────

    @router.message(Command("id"))
    async def cmd_id(message: Message) -> None:
        target = message.reply_to_message
        if target:
            uid  = target.from_user.id
            name = target.from_user.full_name
            await message.reply(f"🆔 <b>{name}</b>\nID: <code>{uid}</code>", parse_mode="HTML")
        else:
            uid  = message.from_user.id
            cid  = message.chat.id
            await message.reply(
                f"👤 ID المستخدم: <code>{uid}</code>\n"
                f"💬 ID المجموعة: <code>{cid}</code>",
                parse_mode="HTML",
            )

    return router
