from copy import deepcopy
import glob
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



    def to_dict(self) -> dict:
        return {
            "balance": self.balance,
            "started_playing": self.started_playing,
            "lang": self.lang,
            "name": self.name
        }


# main manager

class Manager:
    def __init__(self, db_file:str, data_file:str, locale_dir:str):
        '''
        Manages basically the entire bot.
        '''
        self.db_file = db_file # path to database file
        self.data_file = data_file # path to data file
        self.locale_dir = locale_dir # path to locale directory

        self.reload_db()


    def clone_db(self):
        '''
        Copies the database into a backup file.
        '''
        with open(self.db_file, encoding='utf8') as f:
            data = f.read()

        with open(f'{self.db_file}.bak', 'w', encoding='utf8') as f:
            f.write(data)


    def commit_db(self):
        '''
        Pushes all data to the database file.
        '''
        data = {
            "users": {
                i: self.users[i].to_dict() for i in self.users
            }
        }
        with open(self.db_file, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False)


    def create_db(self):
        '''
        Creates the database if one doesn't exist or is corrupted.
        '''
        self.users: Dict[int, User] = {}

        self.commit_db()


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

        self.commit_db()


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
        self.commit_db()


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
                self.commit_db()
        
        return botuser
    

    def set_locale(self, id:int, key:str):
        '''
        Sets the user's language.
        '''
        user = self.get_user(id)

        user.lang = key

        self.commit_db()


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

        self.commit_db()
        return True
        

    def give_money(self, id:int, amount:int):
        '''
        Gives money to the user.
        '''
        user = self.get_user(id)
        user.balance += amount
        self.commit_db()
