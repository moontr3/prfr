from copy import deepcopy
import glob
import threading
from typing import *

import os
import json
from config import *
from utils import *
import time
from aiogram.types import User as AiogramUser
from aiogram.types import Message as AiogramMessage
import random
from log import *
import utils

# locale

class Locale:
    def __init__(self,
        filename: str
    ):
        '''
        Represents a locale.
        '''
        self.filename: str = filename
        self.strings: Dict[str,str] = {}
        self.key: str = filename.replace('\\','/').split('/')[-1].split('.')[0]
        self.load()


    def f(self, key:str, *args, **kwargs):
        '''
        Gets a string by a key and formats it.
        '''
        if key not in self.strings:
            return key
        return self.strings[key].format(*args, **kwargs)


    def load(self):
        '''
        Loads a locale from file.
        '''
        with open(self.filename, encoding='utf8') as f:
            data: str = f.read()

        data = data.replace('\\\n', '').split('\n')
        data = [i.replace('\\n','\n') for i in data]

        self.title: str = data[0]
        self.emoji: str = data[1]
        self.strings: Dict[str,str] = {}
        self.const: Dict[str,str] = {}

        # strings
        for i in data[2:]:
            if i == '':
                continue

            if i.startswith('#'):
                continue

            if i.startswith('!'):
                self.const[i.split('=')[0][1:]] = '='.join(i.split('=')[1:])
                continue
                
            text = '='.join(i.split('=')[1:])
            for k, v in self.const.items():
                text = text.replace(f'[{k}]', v)

            self.strings[i.split('=')[0]] = text


# user

class User:
    def __init__(
        self, id:int,
        balance: int = 0,
        started_playing: int = None,
        lang: str = 'en',
        name: str = None,
        name_changed: bool = False,
        pos: Tuple[int,int] = DEFAULT_POS,
        game_name: str | None = None,
        remote: bool = False
    ):
        '''
        A user entry in a database
        '''
        self.id: int = int(id) # telegram user id
        self.name: str = name if name else str(id)
        self.name_changed: bool = name_changed
        self.lang: str = lang
        self.balance: int = balance
        self.started_playing: int = started_playing if started_playing else time.time()
        self.remote: bool = remote
        
        self.pos: Tuple[int,int] = pos
        self.game_name: str | None = game_name


    @property
    def avatar(self) -> str:
        '''
        Returns the player's avatar.
        '''
        return '👶'


    @property
    def display_name(self) -> str:
        '''
        Returns the player's name to display in lists etc.
        '''
        return f'{self.avatar} {self.game_name}'


    def to_dict(self) -> dict:
        return {
            "balance": self.balance,
            "started_playing": self.started_playing,
            "lang": self.lang,
            "name": self.name,
            "pos": self.pos,
            "game_name": self.game_name,
            "remote": self.remote
        }
    

# map

class Map:
    def __init__(self, map_data: str):
        '''
        World map.
        '''
        self.map_data: str = map_data
        self.load_data()


    def load_data(self):
        '''
        Loads map data from file.
        '''
        with open(self.map_data, encoding='utf-8') as f:
            data = json.load(f)

        self.chunk_size: int = data['chunksize']
        self.chunks: Tuple[int,int] = data['chunks']
        self.size: Tuple[int,int] = [
            self.chunks[0]*self.chunk_size, self.chunks[1]*self.chunk_size
        ]
        self.map_dir: str = data['dir']


    @property
    def blank_chunk(self) -> List[List[None]]:
        '''
        Returns a completely empty chunk.
        '''
        return [[None for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]


    def get_chunk(self, pos: Tuple[int,int]) -> List[List[str | None]]:
        '''
        Reads a file of a chunk and returns its contents.
        '''
        target = f'{self.map_dir}{pos[1]}/{pos[0]}.chunk'

        if not os.path.exists(target):
            return self.blank_chunk
        
        with open(target) as f:
            data = f.read()

        out = [ [ i if i != '-' else None for i in row.split(';') ] for row in data.split('\n') ]
        return out
    

    def get_rect(self, topleft: Tuple[int,int], size: Tuple[int,int]) -> List[List[str | None]]:
        '''
        Returns a matrix of objects at the specified position.
        '''
        out = []
        chunks: Dict[str, List[List[str | None]]] = {}

        for y in range(topleft[1], topleft[1]+size[1]):
            row = []
            if y > self.size[1]: y -= self.size[1]
            if y < 0: y += self.size[1]

            for x in range(topleft[0], topleft[0]+size[0]):
                if x > self.size[0]: x -= self.size[0]
                if x < 0: x += self.size[0]

                chunk = [int(x/self.chunk_size), int(y/self.chunk_size)]
                pos_in_chunk = [x%self.chunk_size, y%self.chunk_size]
                
                # getting chunks
                if str(chunk) not in chunks:
                    chunks[str(chunk)] = self.get_chunk(chunk)

                chunk = chunks[str(chunk)]
                row.append(chunk[pos_in_chunk[1]][pos_in_chunk[0]])

            out.append(row)

        return out
    
    
    def get_rect_around(self, center: Tuple[int,int], extend: int) -> List[List[str | None]]:
        '''
        Returns a matrix of objects around the specified position.
        '''
        center = [center[0]-extend, center[1]-extend]
        return self.get_rect(center, [extend*2+1, extend*2+1])


# object library

class Object:
    def __init__(self, key: str, data: Dict, isair: bool = False):
        '''
        Represents an object on the map.
        '''
        self.key: str = key
        self.emoji: str = data.get('emoji', '▪')
        self.color: Tuple[int,int,int] = data.get('color', (0,0,0))
        self.item_emoji: str = data.get('item_emoji', self.emoji)
        self.fluid: bool = data.get('fluid', False)
        self.collision: bool = data.get('collision', False)

        self.air: bool = isair
        self.button_text: str = self.emoji if not isair else ' '


class ObjectLib:
    def __init__(self, data: Dict[str, Dict]): 
        '''
        Library of objects.
        '''
        self.data: Dict[str, Dict] = {k: Object(k, v) for k, v in data.items()}


    def get(self, key: str) -> Object:
        '''
        Returns an object by its key.
        '''
        if key in self.data:
            return self.data[key]
        
        return Object(None, {}, True)
    


# remotes

class Remote:
    def __init__(self, message: AiogramMessage, user_id: int):
        '''
        Remote.
        '''
        self.message: AiogramMessage = message # message to edit when something happens
        self.user_id: int = user_id # user ID whose remote this is
        self.created_at: float = time.time() # when this remote was created
        self.last_activity: float = time.time() # last activity of the remote
        self.prev_text: str = '' # previous message text
        self.running: bool = True # is the remote running
        self.performed_action: bool = False # was an action performed
        self.changed: bool = True # whether to edit the remote's message or not
        self.chat: List[str] = [] # chat history
        self.last_message: float = 0
        self.menu: str | None = None


    def update_last_activity(self):
        '''
        Updates the last activity timer.
        '''
        self.last_activity = time.time()


# main manager

class Manager:
    def __init__(self, db_file:str, data_file:str, locale_dir:str, map_data:str):
        '''
        Manages basically the entire bot.
        '''
        self.db_file = db_file # path to database file
        self.data_file = data_file # path to data file
        self.locale_dir = locale_dir # path to locale directory
        self.committing: bool = False
        self.map = Map(map_data)
        self.remotes: Dict[int, Remote] = {}

        self.reload_db()


    def clone_db(self):
        '''
        Copies the database into a backup file.
        '''
        with open(self.db_file, encoding='utf8') as f:
            data = f.read()

        with open(f'{self.db_file}.bak', 'w', encoding='utf8') as f:
            f.write(data)


    def _commit(self):
        '''
        Pushes all data to the database file.
        '''
        self.commiting = True

        data = {
            "users": {
                i: self.users[i].to_dict() for i in self.users
            }
        }

        out = json.dumps(data, ensure_ascii=False)
        with open(self.db_file, 'w', encoding='utf8') as f:
            f.write(out)

        self.committing = False


    def commit(self):
        '''
        Pushes all the data to the database file.
        '''
        if self.committing:
            return
        threading.Thread(target=self._commit).start()


    def create_db(self):
        '''
        Creates the database if one doesn't exist or is corrupted.
        '''
        self.users: Dict[int, User] = {}

        self.commit()


    def get_locale(self, key:str) -> Locale:
        '''
        Returns a locale by the key.
        '''
        return self.locales.get(key, self.locales['en'])


    def reload_db(self):
        '''
        Loads the database.
        '''
        # loading static
        with open(self.data_file, encoding='utf8') as f:
            data = json.load(f)

        self.data = data
        self.obj: ObjectLib = ObjectLib(data['obj'])

        self.locales: Dict[str, Locale] = {}

        for i in glob.glob(self.locale_dir+'*.lang'):
            key = i.replace('\\','/').split('/')[-1].split('.')[0]
            self.locales[key] = Locale(i)

        # checking if database exists
        if not os.path.exists(self.db_file):
            self.create_db()
            return

        # reading the database
        try:
            with open(self.db_file, encoding='utf8') as f:
                raw_db: dict = json.load(f)
        # creating the database
        except:
            self.clone_db()
            self.create_db()
            return

        # loading data
        users = raw_db.get('users', {})
        self.users: Dict[int, User] =\
            {int(i): User(id=i, **users[i]) for i in users}

        self.commit()


    def new_user(self, id:int, user:AiogramUser):
        '''
        Creates a new user.
        '''
        if id in self.users:
            return
        
        self.users[id] = User(id,
            name=user.first_name if user else None,
            lang=user.language_code if user and\
                user.language_code in self.locales.keys() else "ru"
        )
        self.commit()


    def get_user(self, id:"AiogramUser | int") -> User:
        '''
        Returns a user if found in the database.
        Otherwise creates a new user.

        If AiogramUser is passed in, it's id will be used and
        some calculations will be done.
        '''
        user = None
        if isinstance(id, AiogramUser):
            user = id
            id = id.id

        assert id not in [136817688, 1087968824, 777000], "Blocked ID!"

        if id not in self.users:
            if user == None:
                raise 'User is not in DB!'
            self.new_user(id, user)

        botuser = self.users[id]
        if user:
            if not botuser.name_changed and botuser.name != user.first_name:
                botuser.name = user.first_name
                self.commit()
        
        return botuser
    

    def set_locale(self, id:int, key:str):
        user = self.get_user(id)
        log(f'{user.game_name} ({user.id}) changed language to {key}')
        user.lang = key
        self.commit()


    def get_player_overlay(self, topleft: Tuple[int,int], size: Tuple[int,int]) -> List[List[str | None]]:
        '''
        Returns an overlay of players as a matrix,
        where None is a transparent tile and a str is a player.
        '''
        out = [
            [ [] for _ in range(size[0]) ]\
            for _ in range(size[1])
        ]

        bottomright = [topleft[0]+size[0], topleft[1]+size[1]]
    
        # putting players in matrix
        for i in self.remotes:
            user = self.get_user(i)
            
            # checking if the player is in bounds
            if user.pos[0] >= topleft[0] and\
                user.pos[0] < bottomright[0] and\
                user.pos[1] >= topleft[1] and\
                user.pos[1] < bottomright[1]:
                    # putting player in matrix
                    relpos = [user.pos[0]-topleft[0], user.pos[1]-topleft[1]]
                    out[relpos[1]][relpos[0]].append(user)

        # converting matrix of users to matrix of strings
        textout = []

        for row in out:
            outrow = []

            for col in row:
                if len(col) == 0:
                    outrow.append(None)
                elif len(col) == 1:
                    outrow.append(col[0].avatar)
                else:
                    outrow.append(utils.int_to_emoji(len(col)))

            textout.append(outrow)

        return textout


    def check_remote(self, id:int, action: bool = True):
        if id not in self.remotes or not self.remotes[id].running:
            return 'callback_err_remote_doesnt_exist'
        
        if action:
            remote = self.remotes[id]

            if remote.performed_action:
                return 'callback_err_remote_wait_for_edit'
            remote.performed_action = True

        return True
    

    def change_game_name(self, id:int, name:str):
        user = self.get_user(id)
        log(f'{user.game_name} ({user.id}) changed name to {name}')
        user.game_name = name
        self.commit()
    

    def change_remote_type(self, id:int):
        user = self.get_user(id)
        user.remote = not user.remote

        if id in self.remotes:
            self.remotes[id].changed = True

        self.commit()
    

    def broadcast_user(self, key: str, user_id: int):
        user = self.get_user(user_id)
        
        # broadcasting
        for i in self.remotes.values():
            if i.user_id == user_id: continue

            currentuser = self.get_user(i.user_id)
            l = self.get_locale(currentuser.lang)
            i.chat.append(l.f(key, user=user.game_name))
    

    def send_to_chat(self, l:Locale, id:str, message:str):
        if id not in self.remotes: return
        remote = self.remotes[id]
        
        # checking message
        if len(message) > MAX_CHAT_LENGTH:
            remote.chat.append(l.f('err_chat_message_too_long', max=MAX_CHAT_LENGTH))
            return
        
        if time.time()-remote.last_message < CHAT_TIMEOUT:
            remote.chat.append(l.f('err_chat_message_timeout'))
            return
        
        # broadcasting
        user = self.get_user(id)
        remote.last_message = time.time()
        message = utils.demarkup(message)
        log(f'{user.game_name} ({user.id}) - {message}', level=CHAT)

        for i in self.remotes.values():
            em = '🗨' if i.user_id == id else '💬'
            i.chat.append(f'{user.game_name} {em} {message}')


    def move(self, id:int, offsetx:int, offsety:int):
        user = self.get_user(id)

        # checking distance
        dst = abs(offsetx)+abs(offsety)

        if dst > 2:
            return 'callback_err_remote_move_too_big'
        
        if dst == 0:
            return

        # moving
        user.pos[0] += offsetx
        user.pos[1] += offsety

        if user.pos[0] > self.map.size[0]:
            user.pos[0] -= self.map.size[0]
        if user.pos[1] > self.map.size[1]:
            user.pos[1] -= self.map.size[1]

        if user.pos[1] < 0:
            user.pos[1] += self.map.size[0]
        if user.pos[1] < 0:
            user.pos[1] += self.map.size[1]

        self.remotes[id].update_last_activity()
        self.commit()


    def pay_money(self, author:int, id:int, amount:int) -> bool:
        '''
        Pays money to the user.
        '''
        user = self.get_user(id)
        author = self.get_user(author)

        if author.balance < amount:
            return False

        author.balance -= amount
        user.balance += amount

        self.commit()
        return True
        

    def give_money(self, id:int, amount:int):
        '''
        Gives money to the user.
        '''
        user = self.get_user(id)
        user.balance += amount
        self.commit()
