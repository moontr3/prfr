LOG_FILE = 'log.txt'
ADMINS = [1365781815]
DEFAULT_POS = [43,32]
MAX_NAME_LENGTH = 16
MAX_AFK_TIME_SECONDS = 60*5
REMOTE_BUTTONS = [
    [' ', ' ', '⏫️', ' ', ' '],
    [' ', '↖️', '🔼', '↗️', ' '],
    ['⏪️', '◀️', ' ', '▶️', '⏩️'],
    [' ', '↙️', '🔽', '↘️', ' '],
    [' ', ' ', '⏬️', ' ', ' '],
]
CHAT_HISTORY = 5
CHAT_HISTORY_MENU = 25
MAX_CHAT_LENGTH = 10088
CHAT_TIMEOUT = 1
DAYDREAM_ENERGY_EVERY_SECONDS = 5
DEFAULT_SKIN = '👶'

DEFAULT_ENERGY = 150
DEFAULT_MAX_ENERGY = 200
DEFAULT_MAX_WEIGHT = 1000

# progress bar styles

class Style:
    def __init__(self, left: str, mid: str, right: str, chop_corners: bool):
        self.left: str = left
        self.mid: str = mid
        self.right: str = right
        self.chop_corners: bool = chop_corners
        
STYLES: dict[str, Style] = {
    'default': Style(' ## ', '#  #', ' ## ', True),
    'square':  Style('####', '#  #', '####', True),
    'tb':      Style('    ', '    ', '#  #', False),
    'bottom':  Style('    ', '    ', '   #', False),
    'mid':     Style('    ', '    ', ' ## ', False),
}