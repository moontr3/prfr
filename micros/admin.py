
import time
from typing import *

from aiogram import F, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import *
import api
import utils

from loader import dp, mg, bot


@dp.message(Command('reindex_names_yes_i_am_sure'))
async def reindex_names(msg: types.Message):
    '''
    Rename every single user in the database to their name.
    '''
    if msg.from_user.id not in ADMINS:
        return
    
    message = await msg.reply(f'<code>#</code> <i>to convert {len(mg.users)} users</i>')

    for v in mg.users.values():
        if not v.name_changed:
            try:
                user = await bot.get_chat(v.id)
            except:
                print(f'! {v.id} - error')
            else:
                print(f'  {v.id} - success - {user.first_name}')
                v.name = user.first_name

    mg.commit_db()

    await message.edit_text(f'<code>#</code> <i>done</i>')


@dp.message(Command('give'))
async def give(msg: types.Message):
    '''
    Give money.
    '''
    if msg.from_user.id not in ADMINS:
        return

    if len(msg.text.split(' ')) < 2:
        return
    
    # amount
    amount = msg.text.split(' ')[1]
    try:
        amount = int(amount)
    except:
        return
    
    # user
    if msg.reply_to_message != None:
        user = msg.reply_to_message.from_user.id
        mention = utils.mention(msg.reply_to_message.from_user.id, msg.reply_to_message.from_user.first_name)
    else:
        user = msg.from_user.id
        mention = utils.mention(msg.from_user.id, msg.from_user.first_name)

    mg.give_money(user, amount)

    await msg.reply(f'<code>#</code> <i>{amount} given to {mention}</i>')
