import sys
import time
import logging

try:
import kurigram
except ImportError:
import pyrogram as kurigram
sys.modules["kurigram"] = kurigram

from kurigram import filters
from kurigram.types import Message, CallbackQuery, LinkPreviewOptions

import config
from main.plugins.keyboard.inline import (
start_keyboard,
back_to_start_keyboard,
close_keyboard,
cb_data
)
from main.services.cache_service import cache

logger = logging.getLogger("MistralBot.Start")

START_TEXT = (
"🌸 <b>Hey there, {name}!</b> 😏💖\n\n"
"I am your flirty anime girl companion powered by <b>Mistral AI</b>! ✨\n\n"
"💬 <i>Send me any message in your favorite language and let's chat!</i>\n\n"
"✨ <b>Menu Options:</b>\n"
"• Chat with me here directly or add me to groups.\n"
"• Type /id to inspect Telegram IDs (Rose bot style).\n"
"• Type /help to view command list."
)

HELP_TEXT = (
"📖 <b>How to Use Me:</b> 💖\n\n"
"🌸 <b>Chatting:</b>\n"
"• Send me any message in private and I will reply to you in your language!\n"
"• In group chats, tag me or reply to my message.\n\n"
"🆔 <b>Commands:</b>\n"
"• <code>/start</code> - Welcome menu\n"
"• <code>/help</code> - Help guide\n"
"• <code>/id</code> - Rose-style Telegram ID lookup\n"
"• <code>/ping</code> - Latency and system stats\n"
"• <code>/setting</code> - <i>(Owner Only)</i> Modify AI temperature, model, and prompt"
)

ABOUT_TEXT = (
"✨ <b>About Me:</b>\n\n"
"🌸 <b>Personality:</b> Flirty, witty Anime Companion\n"
"⚡ <b>Engine:</b> Kurigram (MTProto)\n"
"🧠 <b>AI Core:</b> Mistral AI (Strict JSON)\n"
"⏱️ <b>Response Cache:</b> 30-Minute High-Speed Cache\n"
"🛡️ <b>Security:</b> Full token and secret shielding"
)

LINK_PREVIEW_DISABLED = LinkPreviewOptions(is_disabled=True)

@kurigram.Client.on_message(filters.command(["start"]))
async def start_handler(client, message: Message):
user_id = message.from_user.id if message.from_user else 0
name = message.from_user.first_name if message.from_user else "Darling"
is_owner = user_id in config.OWNER_IDS
await message.reply_text(
START_TEXT.format(name=name),
reply_markup=start_keyboard(is_owner=is_owner),
link_preview_options=LINK_PREVIEW_DISABLED
)

@kurigram.Client.on_message(filters.command(["help"]))
async def help_handler(client, message: Message):
await message.reply_text(
HELP_TEXT,
reply_markup=back_to_start_keyboard(),
link_preview_options=LINK_PREVIEW_DISABLED
)

@kurigram.Client.on_message(filters.command(["ping"]))
async def ping_handler(client, message: Message):
start = time.perf_counter()
msg = await message.reply_text("⚡ <i>Checking connection...</i>")
delta_ms = round((time.perf_counter() - start) * 1000, 2)
stats = cache.stats
ping_text = (
f"🏓 <b>Pong!</b> <code>{delta_ms} ms</code>\n\n"
f"⏳ <b>Uptime:</b> <code>{client.uptime}</code>\n"
f"🤖 <b>AI Model:</b> <code>{config.ai_settings.model}</code>\n"
f"🌡️ <b>Temperature:</b> <code>{config.ai_settings.temperature}</code>\n"
f"⚡ <b>Cache Entries:</b> <code>{stats['cached_entries']}</code> (Hits: {stats['hits']})\n"
f"⏱️ <b>Cache TTL:</b> <code>{stats['ttl_minutes']} mins</code>"
)
await msg.edit_text(ping_text, reply_markup=close_keyboard())

@kurigram.Client.on_callback_query(cb_data(r"^start_menu$"))
async def callback_start_menu(client, callback: CallbackQuery):
user_id = callback.from_user.id
name = callback.from_user.first_name or "Darling"
is_owner = user_id in config.OWNER_IDS
await callback.message.edit_text(
START_TEXT.format(name=name),
reply_markup=start_keyboard(is_owner=is_owner),
link_preview_options=LINK_PREVIEW_DISABLED
)
await callback.answer()

@kurigram.Client.on_callback_query(cb_data(r"^help_menu$"))
async def callback_help_menu(client, callback: CallbackQuery):
await callback.message.edit_text(
HELP_TEXT,
reply_markup=back_to_start_keyboard(),
link_preview_options=LINK_PREVIEW_DISABLED
)
await callback.answer()

@kurigram.Client.on_callback_query(cb_data(r"^about_menu$"))
async def callback_about_menu(client, callback: CallbackQuery):
await callback.message.edit_text(
ABOUT_TEXT,
reply_markup=back_to_start_keyboard(),
link_preview_options=LINK_PREVIEW_DISABLED
)
await callback.answer()

@kurigram.Client.on_callback_query(cb_data(r"^ping_status$"))
async def callback_ping_status(client, callback: CallbackQuery):
start = time.perf_counter()
stats = cache.stats
delta_ms = round((time.perf_counter() - start) * 1000, 2)
ping_text = (
f"🏓 <b>Pong!</b> <code>{delta_ms} ms</code>\n\n"
f"⏳ <b>Uptime:</b> <code>{client.uptime}</code>\n"
f"🤖 <b>AI Model:</b> <code>{config.ai_settings.model}</code>\n"
f"🌡️ <b>Temperature:</b> <code>{config.ai_settings.temperature}</code>\n"
f"⚡ <b>Cache Entries:</b> <code>{stats['cached_entries']}</code>\n"
f"🎯 <b>Cache Hit Ratio:</b> <code>{stats['hit_ratio_percent']}%</code>\n"
f"⏱️ <b>TTL Expiry:</b> <code>{stats['ttl_minutes']} mins</code>"
)
await callback.message.edit_text(
ping_text,
reply_markup=back_to_start_keyboard()
)
await callback.answer("Status refreshed! ✨")

@kurigram.Client.on_callback_query(cb_data(r"^close_menu$"))
async def callback_close_menu(client, callback: CallbackQuery):
try:
await callback.message.delete()
except Exception:
await callback.answer("Closed.")
