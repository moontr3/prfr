
import asyncio
import random
import time
from typing import *

from aiogram import F, types
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.utils.deep_linking import decode_payload
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import *
import api
import utils

from loader import dp, mg, bot

from .texts import *
from .keyboards import *



@dp.message(Command('login'))
async def remote(msg: types.Message):
    '''
    starts a remote.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    if msg.chat.type != 'private':
        await msg.reply(l.f('err_remote_not_private'))
        return
    elif user.id in mg.remotes:
        await msg.reply(l.f('err_remote_exists'))
        return
    
    # mg.start_remote(user.id)

    await msg.reply(l.f('general_loading'))


@dp.message(Command('a'))
async def a(msg: types.Message):
    '''
    a.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    msg = await msg.reply('0')

    for i in range(65):
        try:
            await msg.edit_text(str(i+1))
            await asyncio.sleep(0.8)
        except Exception as e:
            print(e)