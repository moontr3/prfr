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
        remote: bool = False,
        energy: int = DEFAULT_ENERGY,
        max_energy: int = DEFAULT_MAX_ENERGY,
        max_weight: int = DEFAULT_MAX_WEIGHT,
        inventory: Dict[str, int] = {},
        skin: str = DEFAULT_SKIN
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
        self.skin: str = skin
        
        self.pos: Tuple[int,int] = pos
        self.game_name: str | None = game_name
        self.energy: int = energy
        self.max_energy: int = max_energy
        self.inventory: Dict[str, int] = inventory
        self.max_weight: int = max_weight


    @property
    def avatar(self) -> str:
        return self.skin

    @property
    def pb_style(self) -> str:
        return 'default'

    @property
    def display_name(self) -> str:
        '''
        Returns the player's name to display in lists etc.
        '''
        return f'{self.avatar} {self.game_name}'

    def get_energy_pb(self) -> str:
        return utils.progress_bar(
            self.energy, self.max_energy, '⚡', self.pb_style
        )
    

    def add_to_inventory(self, item: str, amount: int):
        '''
        Adds the item to inventory.
        '''
        if item not in self.inventory:
            self.inventory[item] = amount
        else:
            self.inventory[item] += amount


    def remove_from_inventory(self, item: str, amount: int):
        '''
        Removes the item from inventory.
        '''
        if item not in self.inventory:
            return
        
        self.inventory[item] -= amount
        if self.inventory[item] <= 0:
            del self.inventory[item]


    def to_dict(self) -> dict:
        return {
            "balance": self.balance,
            "started_playing": self.started_playing,
            "lang": self.lang,
            "name": self.name,
            "pos": self.pos,
            "game_name": self.game_name,
            "remote": self.remote,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "max_weight": self.max_weight,
            "inventory": self.inventory,
            "skin": self.skin
        }
    

# map

class MapObject:
    def __init__(self, data: str):
        '''
        A tile on the map.
        '''
        args = data.split(',')
        self.obj: str | None = args[0] if args[0] != '-' else None
        self.durability: int | None = int(args[1]) if len(args) > 1 else None
        self.isair: bool = self.obj == None

    def to_string(self) -> str:
        # air
        if self.isair:
            return '-'
        
        # object data
        out = self.obj

        if self.durability:
            out += f',{self.durability}'

        return out

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


    def save_chunk(self, pos: Tuple[int,int], data: List[List[MapObject]]):
        '''
        Loads map data from file.
        '''
        out = '\n'.join([ ';'.join([i.to_string() for i in row]) for row in data ])

        with open(f'{self.map_dir}{pos[1]}/{pos[0]}.chunk', 'w') as f:
            f.write(out)


    @property
    def blank_chunk(self) -> List[List[MapObject]]:
        '''
        Returns a completely empty chunk.
        '''
        return [[MapObject('-') for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]


    def get_chunk(self, pos: Tuple[int,int]) -> List[List[MapObject]]:
        '''
        Reads a file of a chunk and returns its contents.
        '''
        target = f'{self.map_dir}{pos[1]}/{pos[0]}.chunk'

        if not os.path.exists(target):
            return self.blank_chunk
        
        with open(target) as f:
            data = f.read()

        out = [
            [ MapObject(i) for i in row.split(';') ]\
                for row in data.split('\n')
        ]
        return out
    

    def get_rect(self, topleft: Tuple[int,int], size: Tuple[int,int]) -> List[List[MapObject]]:
        '''
        Returns a matrix of objects at the specified position.
        '''
        out = []
        chunks: Dict[str, List[List[MapObject]]] = {}

        for y in range(topleft[1], topleft[1]+size[1]):
            row = []
            if y >= self.size[1]: y -= self.size[1]
            if y < 0: y += self.size[1]

            for x in range(topleft[0], topleft[0]+size[0]):
                if x >= self.size[0]: x -= self.size[0]
                if x < 0: x += self.size[0]

                chunk = [int(x/self.chunk_size), int(y/self.chunk_size)]
                pos_in_chunk = [x%self.chunk_size, y%self.chunk_size]
                
                # getting chunks
                if str(chunk) not in chunks:
                    chunks[str(chunk)] = self.get_chunk(chunk)

                chunk = chunks[str(chunk)]
                obj = chunk[pos_in_chunk[1]][pos_in_chunk[0]]
                row.append(obj)

            out.append(row)

        return out
    

    def get_tile(self, pos: Tuple[int,int]) -> MapObject:
        '''
        Returns an object at a position.
        '''
        x = pos[0]
        y = pos[1]

        chunk = [int(x/self.chunk_size), int(y/self.chunk_size)]
        pos_in_chunk = [x%self.chunk_size, y%self.chunk_size]
        
        chunk_data = self.get_chunk(chunk)
        return chunk_data[pos_in_chunk[1]][pos_in_chunk[0]]
    
    
    def get_rect_around(self, center: Tuple[int,int], extend: int) -> List[List[MapObject]]:
        '''
        Returns a matrix of objects around the specified position.
        '''
        center = [center[0]-extend, center[1]-extend]
        return self.get_rect(center, [extend*2+1, extend*2+1])


# object library

class ItemDrop:
    def __init__(self, data: Dict):
        '''
        A possible item drop
        '''
        self.item: str = data['item']
        self.amount: Range = Range(data.get('amount', 1))
        self.chance: float = data.get('chance', 1)


    def get_drop(self) -> int | None:
        if random.random() > self.chance:
            return
        
        amount = self.amount.get()
        if amount <= 0:
            return
        
        return amount

class Object:
    def __init__(self, key: str, data: Dict, isair: bool = False):
        '''
        Represents an object on the map.
        '''
        self.key: str = key
        self.emoji: str = data.get('emoji', '▪')
        self.color: Tuple[int,int,int] = data.get('color', (0,0,0))
        self.fluid: bool = data.get('fluid', False)
        self.collision: bool = data.get('collision', False)
        self.durability: int = data.get('durability', 0)
        self.drops: List[ItemDrop] = [ItemDrop(i) for i in data.get('drops', [])]
        self.max_drops: int | None = data.get('max_drops', None)

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


# item library

class Item:
    def __init__(self, key: str, data: Dict):
        '''
        Represents an item.
        '''
        self.key: str = key
        self.emoji: str = data.get('emoji', '❓')
        self.weight: int = data.get('weight', 0)
        food = data.get('food', None)
        self.food: Range | None = Range(food) if food else None
        self.block: str | None = data.get('block', None)


class ItemLib:
    def __init__(self, data: Dict[str, Dict]): 
        '''
        Library of items.
        '''
        self.data: Dict[str, Dict] = {k: Item(k, v) for k, v in data.items()}


    def get(self, key: str) -> Item:
        '''
        Returns an item by its key.
        '''
        if key in self.data:
            return self.data[key]
        
        return Item(key, {})


# inventory

class InvItem:
    def __init__(self, key: str, amount: int, item: Item):
        '''
        A slot of items in the inventory.
        '''
        self.key: str = key
        self.amount: int = amount
        self.item: Item = item

        self.weight: int = self.amount*self.item.weight


# recipe library

class Recipe:
    def __init__(self, data: Dict):
        '''
        Represents a recipe.
        '''
        self.requires: Dict[str, int] = data['req']
        self.gives: str = data['gives']
        self.amount: int = data.get('amount', 1)
        self.energy: int = data.get('energy', 0)


class RecipeLib:
    def __init__(self, data: List[Dict]): 
        '''
        Library of recipes.
        '''
        self.data: List[Recipe] = [Recipe(v) for v in data]


    def get_craftable(self, inv: Dict[str, int]) -> List[Tuple[Recipe, int]]:
        '''
        Searches recipes and only returns the ones that are craftable
        with the passed in inventory.
        '''
        out = []

        for index, i in enumerate(self.data):
            for key, amount in i.requires.items():
                if key not in inv or inv[key] < amount:
                    break
            else:
                out.append((i, index))
                
        return out


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
        self.inv_selected: str | None = None
        self.menu: str | None = None
        self.durability_current: int = None
        self.durability_item: Object = None
        self.acquired_items: Dict[Item, int] = {}
        self.daydreaming: bool = False
        self.daydream_energy_time: float = time.time()
        self.tick: int = 0
        self.hw_item: int | None = None
        self.hw_made_item: Item | None = None
        self.hw_made_amount: int | None = None


    def update_last_activity(self):
        '''
        Updates the last activity timer.
        '''
        self.last_activity = time.time()


    def reset_data(self):
        '''
        Resets temporary data.
        '''
        self.durability_item = None
        self.durability_current = None
        self.acquired_items: Dict[Item, int] = {}
        self.hw_made_item = None
        self.hw_made_amount = None


    def switch_daydreaming(self):
        '''
        Switches daydreaming on or off.
        '''
        self.daydreaming = not self.daydreaming

        if self.daydreaming:
            self.daydream_energy_time = time.time()


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
        self.item: ItemLib = ItemLib(data['item'])
        self.recipe: RecipeLib = RecipeLib(data['recipes'])

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
    

    def get_inventory(self, user: User) -> List[InvItem]:
        out = []

        for item, amount in user.inventory.items():
            out.append(InvItem(item, amount, self.item.get(item)))

        return out
    

    def set_locale(self, id:int, key:str):
        user = self.get_user(id)
        log(f'{user.game_name} ({user.id}) changed language to {key}')
        user.lang = key
        self.commit()


    def get_player_overlay(self,
        topleft: Tuple[int,int], size: Tuple[int,int], tick: int = 0
    ) -> List[List[str | None]]:
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
                    avatar = col[0].avatar
                    if self.remotes[col[0].id].daydreaming:
                        avatar = '💤'

                    outrow.append(avatar)

                else:
                    outrow.append(utils.int_to_emoji(len(col)))

            textout.append(outrow)

        return textout
    

    def remote_tick(self, user: User, remote: Remote):
        remote.tick += 1

        # daydreaming xp
        if remote.daydreaming:
            if time.time()-remote.daydream_energy_time > DAYDREAM_ENERGY_EVERY_SECONDS:
                remote.daydream_energy_time += DAYDREAM_ENERGY_EVERY_SECONDS

                if user.energy < user.max_energy:
                    user.energy += 1

                self.commit()
                remote.update_last_activity()


    def eat_item(self, user: User, item: InvItem):
        energy = item.item.food.get()

        user.energy += energy
        user.energy = min(user.max_energy, user.energy)
        user.remove_from_inventory(item.key, 1)

        self.commit()


    def check_remote(self, id:int, action: bool = True, daydream: bool = False):
        if id not in self.remotes or not self.remotes[id].running:
            return 'callback_err_remote_doesnt_exist'
        
        if action:
            remote = self.remotes[id]

            if remote.daydreaming and not daydream:
                return 'callback_err_remote_daydreaming'

            if remote.performed_action:
                return 'callback_err_remote_wait_for_edit'
            remote.performed_action = True

        return True
    

    def change_game_name(self, id:int, name:str):
        user = self.get_user(id)
        log(f'{user.game_name} ({user.id}) changed name to {name}')
        user.game_name = name
        self.commit()
    

    def set_handiwork_item(self, id:int, item:str):
        remote = self.remotes[id]
        remote.hw_item = item
        remote.menu = 'handiwork'
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
        remote.last_message = time.time()
        remote.update_last_activity()

        user = self.get_user(id)
        message = utils.demarkup(message)
        log(f'{user.game_name} ({user.id}) - {message}', level=CHAT)

        for i in self.remotes.values():
            em = '🗨' if i.user_id == id else '💬'
            i.chat.append(f'<b>{user.game_name}</b> {em} {message}')

        if len(self.remotes) == 1:
            remote.chat.append(l.f('chat_but_no_one_came'))


    def move(self, id:int, offsetx:int, offsety:int):
        user = self.get_user(id)

        # checking distance
        dst = abs(offsetx)+abs(offsety)

        if dst > 2:
            return 'callback_err_remote_move_too_big'
        
        if dst == 0:
            return
        
        if user.energy <= 0 and dst > 1:
            return 'callback_err_remote_not_enough_energy'

        # checking position
        target_pos = utils.move(user.pos, offsetx, offsety, self.map.size)
        between_pos = utils.move(
            user.pos, max(-1, min(1, offsetx)), max(-1, min(1, offsety)), self.map.size
        )

        target_tile = self.obj.get(self.map.get_tile(target_pos).obj)

        if target_pos == between_pos:
            between_tile = target_tile
        else:
            between_tile = self.obj.get(self.map.get_tile(between_pos).obj)

        if target_tile.collision:
            return 'callback_err_remote_collision'

        if between_tile.collision:
            return 'callback_err_remote_path_blocked'
        
        # moving player
        user.pos = target_pos
        if dst > 1:
            user.energy -= 1

        self.remotes[id].update_last_activity()
        self.commit()


    def destroy(self, id:int, offsetx:int, offsety:int):
        user = self.get_user(id)
        remote = self.remotes[id]

        # checking distance
        dst = abs(offsetx)+abs(offsety)

        if dst > 1:
            return 'callback_err_remote_other'
        
        if dst == 0:
            return
        
        if user.energy <= 0:
            return 'callback_err_remote_not_enough_energy'

        # checking tile
        target_pos = utils.move(user.pos, offsetx, offsety, self.map.size)
        
        chunk = [
            int(target_pos[0]/self.map.chunk_size),
            int(target_pos[1]/self.map.chunk_size)
        ]
        pos_in_chunk = [
            target_pos[0]%self.map.chunk_size,
            target_pos[1]%self.map.chunk_size
        ]
        chunk_data = self.map.get_chunk(chunk)
        map_tile: MapObject = chunk_data[pos_in_chunk[1]][pos_in_chunk[0]]

        target_tile = self.obj.get(map_tile.obj)

        if target_tile.durability <= 0:
            return 'callback_err_remote_not_breakable'
        
        # damaging tile
        if map_tile.durability == None:
            map_tile.durability = target_tile.durability
        map_tile.durability -= 1
        user.energy -= 1

        # breaking
        remote.acquired_items = {}

        if map_tile.durability == 0:
            chunk_data[pos_in_chunk[1]][pos_in_chunk[0]] = MapObject('-')
            remote.reset_data()

            # item drops
            for drop in target_tile.drops:
                amount = drop.get_drop()

                if amount:
                    user.add_to_inventory(drop.item, amount)
                    item = self.item.get(drop.item)
                    remote.acquired_items[item] = amount

                    if target_tile.max_drops != None:
                        if amount >= target_tile.max_drops:
                            break

        else:
            remote.durability_item = target_tile
            remote.durability_current = map_tile.durability

        self.map.save_chunk(chunk, chunk_data)
        self.commit()

        remote.update_last_activity()


    def place(self, id:int, offsetx:int, offsety:int):
        user = self.get_user(id)
        remote = self.remotes[id]

        # checking distance
        if abs(offsetx) > 2 or abs(offsety) > 2:
            return 'callback_err_remote_too_far_away'

        # checking tile
        target_pos = utils.move(user.pos, offsetx, offsety, self.map.size)
        
        chunk = [
            int(target_pos[0]/self.map.chunk_size),
            int(target_pos[1]/self.map.chunk_size)
        ]
        pos_in_chunk = [
            target_pos[0]%self.map.chunk_size,
            target_pos[1]%self.map.chunk_size
        ]
        chunk_data = self.map.get_chunk(chunk)
        map_tile: MapObject = chunk_data[pos_in_chunk[1]][pos_in_chunk[0]]
        target_tile = self.obj.get(map_tile.obj)

        if not map_tile.isair and not target_tile.fluid:
            return 'callback_err_remote_occupied'

        for i in self.remotes:
            currentuser = self.get_user(i)
            if currentuser.pos == target_pos:
                return 'callback_err_remote_player_there'
        
        # checking selected object
        inv = self.get_inventory(user)
        selected = None

        for item in inv:
            if item.key == remote.inv_selected and item.item.block:
                selected = item

        if selected == None:
            return 'callback_err_remote_item_not_chosen'
        if not selected.item.block:
            return 'callback_err_remote_item_not_placeable'

        # placing
        chunk_data[pos_in_chunk[1]][pos_in_chunk[0]] = MapObject(selected.key)
        user.remove_from_inventory(selected.key, 1)

        self.map.save_chunk(chunk, chunk_data)
        self.commit()

        remote.update_last_activity()


    def make_item(self, user: User, recipe: Recipe):
        remote = self.remotes[user.id]

        # checking
        if user.energy < recipe.energy:
            return 'callback_err_remote_not_enough_energy'

        for i, amount in recipe.requires.items():
            if i not in user.inventory or user.inventory[i] < amount:
                return 'callback_err_remote_short_on_items'

        # making
        gives = self.item.get(recipe.gives)
        if not remote.hw_made_item or remote.hw_made_item.key != recipe.gives:
            remote.hw_made_item = gives
            remote.hw_made_amount = 0

        remote.hw_made_amount += recipe.amount

        user.energy -= recipe.energy
        
        for i, amount in recipe.requires.items():
            user.remove_from_inventory(i, amount)
        user.add_to_inventory(recipe.gives, recipe.amount)

        self.commit()
        remote.update_last_activity()


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
