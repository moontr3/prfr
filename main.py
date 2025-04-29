
from typing import *

from config import *

from loader import bot, dp, mg
import micros
import asyncio


print('Started polling...')
asyncio.run(dp.start_polling(bot))