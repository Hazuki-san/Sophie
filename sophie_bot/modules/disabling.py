# Copyright (C) 2019 The Raphielscape Company LLC.
# Copyright (C) 2018 - 2020 MrYacha
#
# This file is part of SophieBot.
#
# SophieBot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.

from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from sophie_bot.decorator import register, COMMANDS_ALIASES
from sophie_bot.services.mongo import db
from .utils.connections import chat_connection
from .utils.disable import DISABLABLE_COMMANDS, disablable_dec
from .utils.language import get_strings_dec
from .utils.message import get_arg, need_args_dec


@register(cmds="disableable")
@disablable_dec('disableable')
@get_strings_dec("disable")
async def list_disablable(message, strings):
	text = strings['disablable']
	for command in DISABLABLE_COMMANDS:
		text += f"* <code>/{command}</code>\n"
	await message.reply(text)


@register(cmds="disabled")
@chat_connection(only_groups=True)
@get_strings_dec("disable")
async def list_disabled(message, chat, strings):
	text = strings['disabled_list'].format(chat_name=chat['chat_title'])

	if not (disabled := await db.disabled_v2.find_one({'chat_id': chat['chat_id']})):
		await message.reply(strings['no_disabled_cmds'].format(chat_name=chat['chat_title']))
		return

	commands = disabled['cmds']
	for command in commands:
		text += f"* <code>/{command}</code>\n"
	await message.reply(text)


@register(cmds="disable", user_admin=True)
@need_args_dec()
@chat_connection(admin=True, only_groups=True)
@get_strings_dec("disable")
async def disable_command(message, chat, strings):
	cmd = get_arg(message).lower()
	if cmd[0] == '/' or cmd[0] == '!':
		cmd = cmd[1:]

	# Check on commands aliases
	for name, keys in COMMANDS_ALIASES.items():
		if cmd in keys:
			cmd = name
			break

	if cmd not in DISABLABLE_COMMANDS:
		await message.reply(strings["wot_to_disable"])
		return

	if await db.disabled_v2.find_one({'chat_id': chat['chat_id'], 'cmds': {'$in': [cmd]}}):
		await message.reply(strings['already_disabled'])
		return

	await db.disabled_v2.update_one(
		{'chat_id': chat['chat_id']},
		{"$addToSet": {'cmds': {'$each': [cmd]}}},
		upsert=True
	)

	await message.reply(strings["disabled"].format(
		cmd=cmd,
		chat_name=chat['chat_title']
	))


@register(cmds="enable")
@need_args_dec()
@chat_connection(admin=True, only_groups=True)
@get_strings_dec("disable")
async def enable_command(message, chat, strings):
	chat_id = chat['chat_id']
	cmd = get_arg(message).lower()
	if cmd[0] == '/' or cmd[0] == '!':
		cmd = cmd[1:]

	# Check on commands aliases
	for name, keys in COMMANDS_ALIASES.items():
		if cmd in keys:
			cmd = name
			break

	if cmd not in DISABLABLE_COMMANDS:
		await message.reply(strings["wot_to_enable"])
		return

	if not await db.disabled_v2.find_one({'chat_id': chat['chat_id'], 'cmds': {'$in': [cmd]}}):
		await message.reply(strings["already_enabled"])
		return

	await db.disabled_v2.update_one(
		{'chat_id': chat_id},
		{'$pull': {'cmds': cmd}}
	)

	await message.reply(strings["enabled"].format(
		cmd=cmd, chat_name=chat['chat_title']
	))


@register(cmds="enableall", is_admin=True)
@chat_connection(admin=True, only_groups=True)
@get_strings_dec("disable")
async def enable_all(message, chat, strings):
	# Ensure that something is disabled
	if not await db.disabled_v2.find_one({'chat_id': chat['chat_id']}):
		await message.reply(strings['not_disabled_anything'].format(chat_title=chat['chat_title']))
		return

	text = strings['enable_all_text'].format(chat_name=chat['chat_title'])
	buttons = InlineKeyboardMarkup()
	buttons.add(InlineKeyboardButton(strings['enable_all_btn_yes'], callback_data='enable_all_notes_cb'))
	buttons.add(InlineKeyboardButton(strings['enable_all_btn_no'], callback_data='cancel'))
	await message.reply(text, reply_markup=buttons)


@register(regexp='enable_all_notes_cb', f='cb', is_admin=True)
@chat_connection(admin=True)
@get_strings_dec('disable')
async def enable_all_notes_cb(event, chat, strings):
	data = await db.disabled_v2.find_one({'chat_id': chat['chat_id']})
	await db.disabled_v2.delete_one({'_id': data['_id']})

	text = strings['enable_all_done'].format(num=len(data['cmds']), chat_name=chat['chat_title'])
	await event.message.edit_text(text)


async def __export__(chat_id):
	disabled = await db.disabled_v2.find_one({'chat_id': chat_id})

	return {'disabled': disabled['cmds'] if disabled else []}
