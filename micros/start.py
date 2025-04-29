
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



@dp.message(CommandStart(deep_link=False))
async def welcome(msg: types.Message):
    '''
    shows welcome.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)
    
    text = l.f('welcome')
    
    await msg.reply(text)