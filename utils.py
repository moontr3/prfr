import datetime
import random
from typing import *
import time as stime
from config import *


def to_superscript(string:str):
    string = str(string)
    replace_from = 'ABDEGHIJKLMNOPRTUVWabcdefghijklmnoprstuvwxyz+-=()0123456789.'
    replace_to =   'ᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ⁺⁻⁼⁽⁾⁰¹²³⁴⁵⁶⁷⁸⁹·'

    for a, b in list(zip(replace_from, replace_to)):
        string = string.replace(a,b)
        
    return string


def shorten_number(num:int) -> str:
    sizes = ['', 'k','m','b','t']

    i = 0
    while num >= 1000 and i < len(sizes)-1:
        num /= 1000
        i += 1

    ptnum = f'{num:.1f}'

    return f'{ptnum if i != 0 else num}{sizes[i]}'


def mention(id:int, user:str=None) -> str:
    text = user if isinstance(user, str) else user.name
    return f'<a href="tg://user?id={id}">{text}</a>'


def time(l, num:int,
    seconds:bool=True,
) -> str:
    '''
    Converts a delta timestamp to a string.
    '''
    times = {
        "dy": 24*3600,
        "hr": 3600,
        "min": 60,
    }
    if seconds:
        times['sec'] = 1

    out = ''

    for st, val in times.items():
        n = 0
        while num >= val:
            num -= val
            n += 1

        if n > 0:
            out += f'{n} {l.f(st)} '

    if out == '':
        out = f'{int(num)} {l.f("sec")} '

    return out[:-1]

def day(l, timestamp:float) -> str:
    '''
    Returns the string-formatted timestamp.
    '''
    dt = datetime.datetime.fromtimestamp(timestamp)

    month = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']

    return f'{dt.day} {l.f(month[dt.month-1])} {dt.year}, {dt.hour}:{dt.minute:0>2}'
    

def card_name(l, card, meta, bold=True, formatting=True, fusion_lvl:int=None, short=False):
    '''
    Formats the card name and returns it.
    '''
    fusion_lvl = card.fusion_level if fusion_lvl == None else fusion_lvl
    flvl_str = '🌟'*int(fusion_lvl/5) + '⭐'*(fusion_lvl%5)

    name = meta.get_name(l) if not short else meta.short
    
    if not formatting:
        return f'[{card.level}] {flvl_str} {name}'
    
    name = f'<b>{name}</b>' if bold else name
    return f'<code>[{card.level}]</code> {flvl_str} {name}'


def progress_bar(current:int, total:int, length:int=10, symbols:str=' ▏▎▍▍▌▋▊▉█') -> str:
    '''
    Returns a progress bar to put in a message.
    '''
    out = ''
    current = min(total, max(0, current))
    current = current/total*length

    for i in range(length):
        item = current-i
        item = min(1, max(0, item))

        out += symbols[int(item*(len(symbols)-1))]

    return out


class Range:
    def __init__(self, x:"float | Tuple[float, float]"):
        '''
        Represents a range value.
        '''
        self.x: "float | Tuple[float, float]" = x
        self.type: str = 'num' if type(x) in [int, float] else\
            'choice' if len(x) > 2 else\
            'rangeint' if type(x[0]) == type(x[1]) == int else 'rangefloat'
        

    def add(self, add:"int | float") -> "Range":
        if self.type == 'num':
            return Range(self.x+add)
        
        return Range([i+add for i in self.x])
    

    def max(self) -> int:
        if self.type == 'num':
            return self.x
        
        return max(self.x)
    

    def min(self) -> int:
        if self.type == 'num':
            return self.x
        
        return min(self.x)
    

    def avg(self) -> int:
        if self.type == 'num':
            return self.x
        
        return round(sum(self.x)/len(self.x))
        

    def __str__(self) -> str:
        if self.type == 'num':
            return str(self.x)
        
        if self.type == 'rangeint':
            return f'{self.x[0]}-{self.x[1]}'
        
        if self.type == 'rangefloat':
            return f'{self.x[0]:.1f}-{self.x[1]:.1f}'
        
        if self.type == 'choice':
            sort = sorted(self.x)
            return f'{sort[0]}..{sort[-1]}'


    def get(self) -> int:
        '''
        Returns a random value.
        '''
        if self.type == 'num':
            return self.x
        
        if self.type == 'rangeint':
            return random.randint(*self.x)
        
        if self.type == 'rangefloat':
            return random.uniform(*self.x)
        
        if self.type == 'choice':
            return random.choice(self.x)
        
def rand_id(k:int=4) -> str:
    '''
    Generates a random unique (probably) hexadecimal string that can be used as an ID.
    '''
    timestamp = str(int(stime.time())) # unique timestamp that changes every second and never repeats after
    random_part = "".join(random.choices('0123456789', k=k)) # randomly generated string to add
                                                             # after the timestamp
    string = hex(int(timestamp+random_part))[2:] # converting the number to hex to make it shorter
    return string