
import random
import time
from typing import *

from aiogram import F, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import *
import api
import utils

from loader import dp, mg, bot

from .texts import *
from .keyboards import *


@dp.message(Command('me'))
async def me(msg: types.Message):
    '''
    info about a user.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    text = l.f('me_stats',
        balance=user.balance,
        time=utils.time(
            l, time.time()-user.started_playing, False
        )
    )

    await msg.reply(text)
