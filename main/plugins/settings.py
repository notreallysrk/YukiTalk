import sys
import logging
from typing import Dict
from html import escape

try:
    import kurigram
except ImportError:
    import pyrogram as kurigram
    sys.modules["kurigram"] = kurigram

from kurigram import filters
from kurigram.types import Message, CallbackQuery, LinkPreviewOptions

import config
from main.plugins.keyboard.inline import (
    settings_main_keyboard,
    temperature_keyboard,
    models_keyboard,
    prompt_keyboard,
    tokens_keyboard,
    cache_keyboard,
    cb_data
)
from main.services.cache_service import cache

logger = logging.getLogger("MistralBot.Settings")
PENDING_PROMPT_USERS: Dict[int, bool] = {}
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


def get_settings_overview() -> str:
    stats = cache.stats
    return (
        "⚙️ <b>A.I. Control & Configuration Panel</b>\n\n"
        f"🤖 <b>Current Model:</b> <code>{escape(str(config.ai_settings.model))}</code>\n"
        f"🌡️ <b>Temperature (Logic/Creativity):</b> <code>{config.ai_settings.temperature}</code>\n"
        f"🔢 <b>Max Generation Tokens:</b> <code>{config.ai_settings.max_tokens}</code>\n"
        f"⚡ <b>Cache Status:</b> <code>{stats['cached_entries']} entries</code> (Hits: <code>{stats['hits']}</code>)\n"
        f"⏱️ <b>Cache TTL:</b> <code>{stats['ttl_minutes']} minutes</code>\n\n"
        "<i>Select any configurable parameter below to modify it on the fly:</i>"
    )


@kurigram.Client.on_message(filters.command(["setting", "settings"]))
async def settings_command_handler(client, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not client.is_owner(user_id):
        await message.reply_text(
            "⛔ <b>Access Denied:</b> This command is restricted to bot owners only."
        )
        return

    await message.reply_text(
        get_settings_overview(),
        reply_markup=settings_main_keyboard(),
        link_preview_options=NO_PREVIEW
    )


@kurigram.Client.on_message(filters.command(["cancel"]) & filters.private)
async def cancel_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id in PENDING_PROMPT_USERS:
        del PENDING_PROMPT_USERS[user_id]
        await message.reply_text(
            "✅ Prompt update cancelled.",
            reply_markup=settings_main_keyboard()
        )
    else:
        await message.reply_text("Nothing to cancel! ✨")


@kurigram.Client.on_message(filters.private & filters.text)
async def receive_custom_prompt(client, message: Message):
    user = message.from_user
    if not user or user.id not in PENDING_PROMPT_USERS:
        return
    if not client.is_owner(user.id):
        PENDING_PROMPT_USERS.pop(user.id, None)
        return

    new_prompt = (message.text or "").strip()
    if not new_prompt:
        await message.reply_text("Please send a non-empty prompt.")
        return
    if len(new_prompt) > 12000:
        await message.reply_text("Prompt is too long. Please keep it under 12000 characters.")
        return

    try:
        config.ai_settings.system_prompt = new_prompt
        PENDING_PROMPT_USERS.pop(user.id, None)
        await message.reply_text(
            "✅ <b>System prompt updated successfully.</b>",
            reply_markup=settings_main_keyboard()
        )
    except Exception:
        logger.exception("Failed to update system prompt")
        await message.reply_text(
            "❌ Failed to update the prompt. Please check the logs."
        )


@kurigram.Client.on_callback_query(cb_data(r"^settings_main$"))
async def cb_settings_main(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    await callback.message.edit_text(
        get_settings_overview(),
        reply_markup=settings_main_keyboard(),
        link_preview_options=NO_PREVIEW
    )
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^setting_temp_menu$"))
async def cb_temperature_menu(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    text = (
        "🌡️ <b>A.I. Logic Ability / Temperature Scale</b>\n\n"
        f"• <b>Current Temperature:</b> <code>{config.ai_settings.temperature}</code>\n\n"
        "• <b>0.2 (Logical & Strict):</b> Factual, precise, less variation.\n"
        "• <b>0.5 (Balanced):</b> Good mix of logic and conversational warmth.\n"
        "• <b>0.7 (Flirty & Anime):</b> Charming, anime girl persona.\n"
        "• <b>1.0+ (Wild & Unpredictable):</b> Highest creativity and randomness.\n\n"
        "<i>Tap a preset or use +/- to fine-tune:</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=temperature_keyboard(config.ai_settings.temperature)
    )
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^set_temp_(\d+(\.\d+)?)$"))
async def cb_set_temperature(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    val = float(callback.matches[0].group(1))
    config.ai_settings.temperature = max(0.1, min(1.5, round(val, 2)))
    await callback.message.edit_reply_markup(
        reply_markup=temperature_keyboard(config.ai_settings.temperature)
    )
    await callback.answer(f"Temperature set to {config.ai_settings.temperature}!")


@kurigram.Client.on_callback_query(cb_data(r"^temp_adjust_(inc|dec)$"))
async def cb_adjust_temperature(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    action = callback.matches[0].group(1)
    current = config.ai_settings.temperature
    new_val = min(1.5, current + 0.1) if action == "inc" else max(0.1, current - 0.1)
    config.ai_settings.temperature = round(new_val, 2)

    await callback.message.edit_reply_markup(
        reply_markup=temperature_keyboard(config.ai_settings.temperature)
    )
    await callback.answer(f"Temperature changed to {config.ai_settings.temperature}!")


@kurigram.Client.on_callback_query(cb_data(r"^setting_model_menu$"))
async def cb_models_menu(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    text = (
        "🤖 <b>Select Mistral AI Model</b>\n\n"
        f"• <b>Active Model:</b> <code>{escape(str(config.ai_settings.model))}</code>\n\n"
        "Choose an available model from the list below:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=models_keyboard(config.ai_settings.model)
    )
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^set_model_(.+)$"))
async def cb_set_model(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    chosen_model = callback.matches[0].group(1)
    config.ai_settings.model = chosen_model
    await callback.message.edit_reply_markup(
        reply_markup=models_keyboard(config.ai_settings.model)
    )
    await callback.answer(f"Switched model to {chosen_model}!")


@kurigram.Client.on_callback_query(cb_data(r"^setting_prompt_menu$"))
async def cb_prompt_menu(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    prompt = config.ai_settings.system_prompt
    prompt_snip = prompt[:180] + ("..." if len(prompt) > 180 else "")
    text = (
        "📝 <b>System Persona / Prompt Settings</b>\n\n"
        f"<b>Current Prompt Preview:</b>\n"
        f"<i>\"{escape(prompt_snip)}\"</i>\n\n"
        "Choose an action below:"
    )
    await callback.message.edit_text(text, reply_markup=prompt_keyboard())
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^prompt_view_full$"))
async def cb_prompt_view_full(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    prompt = escape(str(config.ai_settings.system_prompt))
    text = f"📝 <b>Current Full System Prompt:</b>\n\n<code>{prompt}</code>"
    await callback.message.edit_text(text, reply_markup=prompt_keyboard())
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^prompt_reset_default$"))
async def cb_prompt_reset_default(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    config.ai_settings.reset_prompt()
    await callback.answer("Reset to flirty anime girl persona! 💖", show_alert=True)
    await cb_prompt_menu(client, callback)


@kurigram.Client.on_callback_query(cb_data(r"^prompt_set_custom$"))
async def cb_prompt_set_custom(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    PENDING_PROMPT_USERS[callback.from_user.id] = True
    await callback.message.reply_text(
        "✏️ <b>Enter New System Prompt:</b>\n\n"
        "Please send the new prompt in your next message.\n"
        "<i>(Remember: The AI must be asked to return JSON format "
        "<code>{\"reply\": \"...\"}</code>)</i>\n\n"
        "Send <code>/cancel</code> anytime to abort."
    )
    await callback.answer("Awaiting your new prompt message...")


@kurigram.Client.on_callback_query(cb_data(r"^setting_tokens_menu$"))
async def cb_tokens_menu(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    text = (
        "🔢 <b>Max Output Tokens</b>\n\n"
        f"• <b>Current Limit:</b> <code>{config.ai_settings.max_tokens} tokens</code>\n\n"
        "Limiting tokens reduces Mistral API usage and ensures quick responses."
    )
    await callback.message.edit_text(text, reply_markup=tokens_keyboard(config.ai_settings.max_tokens))
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^set_tokens_(\d+)$"))
async def cb_set_tokens(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    tokens = int(callback.matches[0].group(1))
    config.ai_settings.max_tokens = tokens
    await callback.message.edit_reply_markup(
        reply_markup=tokens_keyboard(config.ai_settings.max_tokens)
    )
    await callback.answer(f"Max tokens set to {tokens}!")


@kurigram.Client.on_callback_query(cb_data(r"^setting_cache_menu$"))
async def cb_cache_menu(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    stats = cache.stats
    text = (
        "⚡ <b>Response Cache Metrics</b>\n\n"
        f"• <b>Cached User Prompts:</b> <code>{stats['cached_entries']}</code>\n"
        f"• <b>Cache Hits:</b> <code>{stats['hits']}</code>\n"
        f"• <b>Cache Misses:</b> <code>{stats['misses']}</code>\n"
        f"• <b>Total Lookups:</b> <code>{stats['total_queries']}</code>\n"
        f"• <b>Hit Ratio:</b> <code>{stats['hit_ratio_percent']}%</code>\n"
        f"• <b>TTL Expiry:</b> <code>{stats['ttl_minutes']} minutes</code>\n\n"
        "<i>Cached responses provide instant replies without using any Mistral tokens.</i>"
    )
    await callback.message.edit_text(text, reply_markup=cache_keyboard())
    await callback.answer()


@kurigram.Client.on_callback_query(cb_data(r"^cache_flush$"))
async def cb_cache_flush(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    cache.clear()
    await callback.answer("Temporary cache flushed completely! 🗑️", show_alert=True)
    await cb_cache_menu(client, callback)


@kurigram.Client.on_callback_query(cb_data(r"^setting_reset_all$"))
async def cb_setting_reset_all(client, callback: CallbackQuery):
    if not client.is_owner(callback.from_user.id):
        return await callback.answer("Unauthorized.", show_alert=True)

    config.ai_settings.temperature = 0.7
    config.ai_settings.model = "open-mistral-7b"
    config.ai_settings.max_tokens = 180
    config.ai_settings.reset_prompt()
    await callback.answer("All settings restored to defaults! 🔄", show_alert=True)
    await cb_settings_main(client, callback)
