
from typing import *

from config import *
import api
from api import Locale
import utils
import time
from loader import mg, bot


def get_server_status_text(l: Locale) -> str:
    text = l.f('status_text')+'\n\n'

    if len(mg.remotes) == 0:
        text += l.f('status_desc_no_players_online')
    else:
        text += l.f('status_desc_players_online', online=len(mg.remotes))

        for i in mg.remotes.values():
            user = mg.get_user(i.user_id)
            text += f'\n•  {user.display_name}'

    return text