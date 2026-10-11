import sys
import logging
import asyncio

try:
    import kurigram
except ImportError:
    import pyrogram as kurigram
    sys.modules["kurigram"] = kurigram

from kurigram import filters, enums
from kurigram.types import Message

import config
from main.services.cache_service import cache
from main.services.mistral_service import mistral_service
from main.plugins.settings import PENDING_PROMPT_USERS

logger = logging.getLogger("MistralBot.ChatHandler")

@kurigram.Client.on_message(filters.text & ~filters.command(["start", "help", "ping", "id", "setting", "settings", "cancel"]))
async def ai_message_handler(client, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    raw_text = (message.text or "").strip()

    if not raw_text:
        return

    if user_id in PENDING_PROMPT_USERS:
        del PENDING_PROMPT_USERS[user_id]
        config.ai_settings.system_prompt = raw_text
        await message.reply_text(
            "✅ <b>Custom System Prompt Updated!</b> 💖\n\n"
            f"<i>\"{raw_text[:200]}...\"</i>",)
        return

    is_private = message.chat.type == enums.ChatType.PRIVATE
    bot_id = client.me.id if client.me else 0
    bot_username = (client.me.username or "").lower() if client.me else ""

    is_reply_to_bot = bool(
        message.reply_to_message and
        message.reply_to_message.from_user and
        message.reply_to_message.from_user.id == bot_id
    )
    is_mentioned = bool(bot_username and f"@{bot_username}" in raw_text.lower())

    if not is_private and not is_reply_to_bot and not is_mentioned:
        return

    clean_text = raw_text
    if is_mentioned and bot_username:
        clean_text = raw_text.replace(f"@{bot_username}", "").replace(f"@{client.me.username}", "").strip()

    if not clean_text:
        await message.reply_text("Hey there handsome, what's on your mind? 😏💖")
        return

    if len(clean_text) > config.MAX_INPUT_LENGTH:
        await message.reply_text(
            f"Aww darling, that's a bit too long for me to read all at once! 💕\n"
            f"Please keep messages under <b>{config.MAX_INPUT_LENGTH} characters</b> so we can chat smoothly 😏✨",)
        return

    cached_reply = cache.get(clean_text)
    if cached_reply:
        try:
            await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
            await message.reply_text(cached_reply,)
        except Exception as e:
            logger.error(f"Error sending cached response: {e}")
        return

    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
    except Exception:
        pass

    try:
        sweet_reply, error_info = await mistral_service.generate_response(clean_text)

        if error_info:
            log_payload = (
                f"⚠️ <b>Mistral Service Notice</b>\n"
                f"👤 <b>User:</b> <code>{user_id}</code>\n"
                f"👥 <b>Chat:</b> <code>{message.chat.id}</code>\n"
                f"❓ <b>Query:</b> <code>{clean_text[:100]}</code>\n"
                f"🚨 <b>Error:</b> <code>{error_info}</code>"
            )
            asyncio.create_task(client.send_log(log_payload))
        else:
            cache.set(clean_text, sweet_reply)

        await message.reply_text(sweet_reply,)

    except Exception as e:
        logger.error(f"Unexpected chat handler error: {e}", exc_info=True)
        error_log = (
            f"❌ <b>Unhandled Chat Exception</b>\n"
            f"👤 <b>User:</b> <code>{user_id}</code>\n"
            f"🚨 <b>Details:</b> <code>{type(e).__name__}: {str(e)}</code>"
        )
        asyncio.create_task(client.send_log(error_log))
        
        await message.reply_text(
            "Aww darling, *blushes* my thoughts got a little tangled! 💕 Say that again, okay? 😏",)
            
