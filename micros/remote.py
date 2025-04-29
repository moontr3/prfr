
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
    shows map around player.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    pos = [user.pos[0]-7, user.pos[1]-7]
    data = mg.map.get_rect(pos, (15,15))

    text = ''

    for row in data:
        text += ''.join([mg.obj.get(i).emoji for i in row])
        text += '\n'

    await msg.reply(text)