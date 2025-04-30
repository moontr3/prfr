
from typing import *

from config import *

from loader import bot, dp, mg
import micros
import asyncio
from log import *


log('Started polling...')
asyncio.run(dp.start_polling(bot))