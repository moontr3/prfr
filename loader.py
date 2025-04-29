
from typing import *

from aiogram import Dispatcher, Bot, client

import os
from dotenv import load_dotenv

from config import *
import api

# loading objects

load_dotenv()
TOKEN = os.getenv('TOKEN')

bot = Bot(TOKEN,
    default=client.default.DefaultBotProperties(
        parse_mode='html'
    )
)
dp = Dispatcher()

mg = api.Manager('users.json', 'data.json', 'lang\\')
