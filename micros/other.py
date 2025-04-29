
import random
from typing import *

from aiogram import types, F

from config import *
import api
from api import Locale
import utils
import time
from loader import mg, dp
from .texts import *


    
@dp.callback_query(F.data == 'discard')
async def inline_discard(call: types.CallbackQuery):
    '''
    Nothing
    '''
    await call.answer()