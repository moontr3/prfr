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
import random

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
        pos: Tuple[int,int] = DEFAULT_POS
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
        
        self.pos: Tuple[int,int] = pos


    @property
    def avatar(self) -> str:
        '''
        Returns the player's avatar.
        '''
        return '👶'


    def to_dict(self) -> dict:
        return {
            "balance": self.balance,
            "started_playing": self.started_playing,
            "lang": self.lang,
            "name": self.name,
            "pos": self.pos
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
        return [[None for _ in range(self.chunk_size[0])] for _ in range(self.chunk_size[1])]


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

            for x in range(topleft[0], topleft[0]+size[0]):
                chunk = [int(x/self.chunk_size), int(y/self.chunk_size)]
                pos_in_chunk = [x%self.chunk_size, y%self.chunk_size]
                
                # getting chunks
                if str(chunk) not in chunks:
                    chunks[str(chunk)] = self.get_chunk(chunk)

                chunk = chunks[str(chunk)]
                row.append(chunk[pos_in_chunk[1]][pos_in_chunk[0]])

            out.append(row)

        return out
    

# object library

class Object:
    def __init__(self, key: str, data: Dict, isair: bool = False):
        '''
        Represents an object on the map.
        '''
        self.key: str = key
        self.emoji: str = data.get('emoji', '▪')
        self.color: Tuple[int,int,int] = data.get('color', (0,0,0))

        self.air: bool = isair
        self.button_text: str = self.emoji if not isair else ''


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
            key = i.split('\\')[-1].split('.')[0]
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
        '''
        Sets the user's language.
        '''
        user = self.get_user(id)

        user.lang = key

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
