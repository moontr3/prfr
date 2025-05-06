
import asyncio
import random
import time
from typing import *
from log import *

from aiogram import F, types
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.utils.deep_linking import decode_payload
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import *
import api
import utils

from loader import dp, mg, bot

from .texts import *
from .keyboards import *


# name changing

@dp.chosen_inline_result()
async def inline_result(q: types.ChosenInlineResult):
    # changing name
    if q.result_id.startswith('namechange:'):
        newname = q.result_id.removeprefix('namechange:')[:MAX_NAME_LENGTH]
        newname = utils.demarkup(newname)
        mg.change_game_name(q.from_user.id, newname)

    # setting hw item
    if q.result_id.startswith('sethwitem:'):
        item = int(q.result_id.removeprefix('sethwitem:'))
        out = mg.check_remote(q.from_user.id)
        if out != True:
            return
        mg.set_handiwork_item(q.from_user.id, item)


@dp.inline_query()
async def inline(q: types.InlineQuery):
    user = mg.get_user(q.from_user.id)
    l = mg.get_locale(user.lang)

    query = q.query
    query1 = q.query.split(' ')

    if len(query1) > 0 and query1[0].lower() in [
        'name', 'hw'
    ]:
        key = query1[0].lower()
        query = ' '.join(query1[1:])

    else:
        await q.answer([types.InlineQueryResultArticle(id='discard',
            title=l.f('inline_unknown_command'),
            input_message_content=types.InputTextMessageContent(
                message_text=l.f(f'inline_discard')
            )
        )], cache_time=5, is_personal=True)
        return
    
    # checking for remote
    if key in ['hw']:
        if user.id not in mg.remotes:
            await q.answer([types.InlineQueryResultArticle(id='discard',
                title=l.f('inline_not_logged_in_title'),
                description=l.f('inline_not_logged_in_desc'),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f('/login')
                )
            )], cache_time=1, is_personal=True)
            return

    # name change query
    if key == 'name':
        if len(query) == 0:
            button = types.InlineQueryResultArticle(id='discard',
                title=l.f('inline_name_change_title'),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f(f'inline_discard')
                )
            )

        elif len(query) > MAX_NAME_LENGTH:
            button = types.InlineQueryResultArticle(id='discard',
                title=l.f('inline_name_change_long_title'),
                description=l.f('inline_name_change_long_desc', max=MAX_NAME_LENGTH),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f(f'inline_discard')
                )
            )

        else:
            button = types.InlineQueryResultArticle(id=f'namechange:{query}',
                title=l.f('inline_name_change_entered_title', name=utils.demarkup(query)),
                description=l.f('inline_name_change_entered_desc'),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f(f'inline_name_changed', name=utils.demarkup(query))
                )
            )

        await q.answer([button], cache_time=5, is_personal=True)
        return

    # crafting item choose
    if key == 'hw':
        items = mg.recipe.get_craftable(user.inventory)

        if len(items) == 0:
            await q.answer([types.InlineQueryResultArticle(id='discard',
                title=l.f('inline_handiwork_no_items_title'),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f(f'inline_discard')
                )
            )], cache_time=1, is_personal=True)
            return

        buttons = [types.InlineQueryResultArticle(id=f'discard',
            title=l.f('inline_handiwork_title', items=len(items)),
            description=l.f('inline_handiwork_desc'),
            input_message_content=types.InputTextMessageContent(
                message_text=l.f(f'inline_discard')
            )
        )]

        for index, i in enumerate(items):
            gives = mg.item.get(i.gives)

            if len(i.requires) > 1:
                desc_items = []
                for item, amount in i.requires.items():
                    item = mg.item.get(item)
                    desc_items.append(f'{item.emoji} {amount}')

                desc = ' ・ '.join(desc_items)
            else:
                item, amount = list(i.requires.items())[0]
                item = mg.item.get(item)
                desc = f'{item.emoji} {l.f(f"item_{item.key}")} ({amount})'

            buttons.append(types.InlineQueryResultArticle(id=f'sethwitem:{index}',
                title=f'{gives.emoji} {l.f(f"item_{gives.key}")} ({i.amount})',
                description=l.f('inline_handiwork_requires', items=desc),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f(
                        f'inline_handiwork_action',
                        item=f'{gives.emoji} {l.f(f"item_{gives.key}")}'
                    )
                )
            ))
        
        await q.answer(buttons, cache_time=1, is_personal=True)
        return
    


# remote message

def get_remote_text(l: api.Locale, remote: api.Remote, user: api.User):
    '''
    Returns the text of the message.
    '''
    text = ''

    # daydreaming title
    if remote.daydreaming:
        text += l.f('remote_daydreaming_title')

        text += '\n'+user.get_energy_pb()
        return text

    # minimap
    if remote.menu in [None, 'break', 'place']:
        data = mg.map.get_rect_around(user.pos, 4)
        topleft = [user.pos[0]-4, user.pos[1]-4]
        overlay = mg.get_player_overlay(topleft, (9,9), remote.tick)

        for y, row in enumerate(data):
            outrow = ''

            for x, i in enumerate(row):
                if overlay[y][x] == None:
                    outrow += mg.obj.get(i.obj).emoji
                else:
                    outrow += overlay[y][x]
        
            text += f'{outrow}\n'

    # place menu
    if remote.menu == 'place':
        inv = mg.get_inventory(user)
        selected = None

        for item in inv:
            if item.key == remote.inv_selected and item.item.block:
                selected = item

        if selected == None:
            text += '\n\n'+l.f('remote_inventory_no_item_selected')

    # stats
    if remote.menu == None:
        text += '\n'+l.f('remote_stats_text', x=user.pos[0], y=user.pos[1])

    # energy bar
    if remote.menu in [None, 'break']:
        text += '\n'+user.get_energy_pb()

    # durability info
    if remote.menu == 'break':
        if remote.durability_item:
            text += '\n'+utils.progress_bar(
                remote.durability_current, remote.durability_item.durability,
                remote.durability_item.emoji, user.pb_style
            )

        if remote.acquired_items:
            out = []
            for item, amount in remote.acquired_items.items():
                out.append(f'{item.emoji} +{amount}')

            text += '\n' + ' ・ '.join(out)

    # chat history
    if remote.menu == 'chat':
        text += l.f('remote_chat_title')+'\n\n'

        if len(remote.chat) == 0:
            text += l.f('remote_chat_empty')

        for i in remote.chat[-CHAT_HISTORY_MENU:]:
            text += f'{i}\n'

    # server info
    if remote.menu == 'server':
        text += get_server_status_text(l)

    # handiwork title
    if remote.menu == 'handiwork':
        if remote.hw_item == None:
            text += l.f('remote_handiwork_search_title')

        else:
            item = mg.recipe.data[remote.hw_item]
            text += l.f('remote_handiwork_title')+'\n\n'
            gives = mg.item.get(item.gives)

            for i, amount in item.requires.items():
                i = mg.item.get(i)
                in_inv = user.inventory.get(i.key, 0)
                if in_inv == 0:
                    in_inv = f'{in_inv}❗'
                text += f'{i.emoji} {l.f(f"item_{i.key}")} <b>×{amount}</b> <i>(🎒 {in_inv})</i>\n'

            text += '—↓—↓—↓—\n'
            text += f'{gives.emoji} {l.f(f"item_{gives.key}")} <b>×{item.amount}</b>'

            if remote.hw_made_item:
                itemname = f'{gives.emoji} {l.f(f"item_{gives.key}")}'
                in_inv = user.inventory.get(gives.key, 0)
                text += '\n\n'+l.f(
                    'remote_handiwork_made_item',
                    item=itemname, amount=item.amount, in_inv=in_inv
                )

            text += '\n\n'+user.get_energy_pb()

    # inventory title
    if remote.menu == 'inventory':
        inv = mg.get_inventory(user)
        weight = sum([i.weight for i in inv])
        items = sum([i.amount for i in inv])

        text += l.f(
            'remote_inventory_title', items=items
        )
        text += '\n'+utils.progress_bar(
            weight, user.max_weight, '⚖', user.pb_style
        )

        # info about selected item
        selitem = [i for i in inv if i.key == remote.inv_selected]

        if selitem:
            selitem = selitem[0]

            text += f'\n\n'+l.f(
                'item_desc',
                emoji=selitem.item.emoji, name=l.f(f'item_{selitem.key}'),
                amount=selitem.amount, weight=selitem.weight, one_weight=selitem.item.weight,
            )
            itemdesckey = f'item_desc_{selitem.key}'
            if itemdesckey in l.strings:
                text += f'\n<blockquote>{l.f(itemdesckey)}</blockquote>'

    # notice
    if remote.menu == 'notice':
        text += l.f('notice')
    
    # chat
    if remote.menu not in ['chat']:
        text += '\n'
        amount = CHAT_HISTORY if remote.menu == None else 1
        for i in remote.chat[-amount:]:
            text += f'\n{i}'

    # remote timeout warning
    if time.time()-remote.last_activity > MAX_AFK_TIME_SECONDS-15:
        text += '\n'+l.f('remote_afk_warning', left=15)

    elif time.time()-remote.last_activity > MAX_AFK_TIME_SECONDS-30:
        text += '\n'+l.f('remote_afk_warning', left=30)

    return text


def get_remote_kb(l: api.Locale, remote: api.Remote, user: api.User) -> InlineKeyboardBuilder:
    '''
    Returns the keyboard of the message.
    '''
    kb = InlineKeyboardBuilder()

    # back button
    if remote.daydreaming:
        kb.add(types.InlineKeyboardButton(
            text=l.f('button_remote_stop_daydream'), callback_data='daydream'
        ))
        return kb

    # walking buttons
    if remote.menu == None:
        data = mg.map.get_rect_around(user.pos, 2)
        topleft = [-2,-2]

        for y, row in enumerate(data):
            buttons = []
            y = topleft[1]+y

            for x, item in enumerate(row):
                x = topleft[0]+x

                if x == 0 and y == 0:
                    text = user.avatar
                elif user.remote:
                    text = REMOTE_BUTTONS[y+2][x+2]
                else:
                    text = mg.obj.get(item.obj).button_text

                buttons.append(types.InlineKeyboardButton(
                    text=text, callback_data=f'move:{x}:{y}'
                ))

            kb.row(*buttons)

        # action buttons
        kb.row(types.InlineKeyboardButton(
            text=l.f('button_remote_break'), callback_data='menu:break'
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f('button_remote_place'), callback_data='menu:place'
        ))

        kb.row(types.InlineKeyboardButton(
            text=l.f('button_remote_inventory'), callback_data='menu:inventory'
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f('button_remote_handiwork'), callback_data='menu:handiwork'
        ))

        # options buttons
        kb.row(types.InlineKeyboardButton(
            text=l.f('button_remote_daydream'), callback_data='daydream'
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f('button_remote_chat'), callback_data='menu:chat'
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f('button_remote_server'), callback_data='menu:server'
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f(f'button_remote_type_{user.remote}'), callback_data='remotetype'
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f('button_remote_logout'), callback_data='logout'
        ))

        kb.row(types.InlineKeyboardButton(
            text=l.f('button_remote_notice'), callback_data='menu:notice'
        ))

    # walking buttons
    elif remote.menu == 'break':
        data = mg.map.get_rect_around(user.pos, 1)
        topleft = [-1,-1]

        for y, row in enumerate(data):
            buttons = []
            y = topleft[1]+y

            for x, item in enumerate(row):
                x = topleft[0]+x

                if x != 0 and y != 0:
                    text = '▪'
                elif x == 0 and y == 0:
                    text = user.avatar
                else:
                    text = mg.obj.get(item.obj).button_text

                buttons.append(types.InlineKeyboardButton(
                    text=text, callback_data=f'break:{x}:{y}'
                ))

            kb.row(*buttons)

        # options buttons
        kb.row(types.InlineKeyboardButton(
            text=l.f('general_back'), callback_data='menu:None'
        ))

    # inventory
    elif remote.menu == 'inventory':
        inv = mg.get_inventory(user)
        selected = None

        for item in inv:
            text = item.item.emoji+utils.to_superscript(str(item.amount))
            text = f'[{text}]' if item.key == remote.inv_selected else text
            if item.key == remote.inv_selected:
                selected = item

            kb.add(types.InlineKeyboardButton(
                text=text, callback_data=f'selectitem:{item.key}'
            ))

        while len(list(kb.buttons)) % 4 != 0:
            kb.add(types.InlineKeyboardButton(
                text=' ', callback_data='discard'
            ))

        kb.adjust(4, repeat=True)

        # selected item actions
        if selected:
            if selected.item.food:
                kb.row(types.InlineKeyboardButton(
                    text=l.f('button_remote_eat', energy=str(selected.item.food)),
                    callback_data=f'itemaction:eat'
                ))
            if selected.item.block:
                kb.row(types.InlineKeyboardButton(
                    text=l.f('button_remote_place'), callback_data='menu:place'
                ))

        # options buttons
        kb.row(types.InlineKeyboardButton(
            text=l.f('general_back'), callback_data='menu:None'
        ))

    # block placement
    elif remote.menu == 'place':
        data = mg.map.get_rect_around(user.pos, 2)
        topleft = [-2,-2]

        for y, row in enumerate(data):
            buttons = []
            y = topleft[1]+y

            for x, item in enumerate(row):
                x = topleft[0]+x
                
                if x == 0 and y == 0:
                    text = user.avatar
                else:
                    text = mg.obj.get(item.obj).button_text

                buttons.append(types.InlineKeyboardButton(
                    text=text, callback_data=f'place:{x}:{y}'
                ))

            kb.row(*buttons)

        # inventory button
        inv = mg.get_inventory(user)
        selected = None

        for item in inv:
            if item.key == remote.inv_selected and item.item.block:
                selected = item

        if selected:
            text = f'{selected.item.emoji} {l.f(f"item_{selected.key}")} ({selected.amount}) ›' 
        else:
            text = l.f('button_remote_place_choose_item')

        kb.row(types.InlineKeyboardButton(
            text=text, callback_data='menu:inventory'
        ))

        # options buttons
        kb.row(types.InlineKeyboardButton(
            text=l.f('general_back'), callback_data='menu:None'
        ))

    # handiwork item search
    elif remote.menu == 'handiwork':
        if remote.hw_item != None:
            item = mg.recipe.data[remote.hw_item]

            for i, amount in item.requires.items():
                if i in user.inventory and user.inventory[i] >= amount and item.energy <= user.energy:
                    if item.energy == 0:
                        text = l.f('button_remote_make')
                    else:
                        text = l.f('button_remote_make_energy', energy=item.energy)
                        
                    kb.row(types.InlineKeyboardButton(
                        text=text, callback_data='makehwitem'
                    ))
                    break

        kb.row(types.InlineKeyboardButton(
            text=l.f('button_remote_handiwork_search'), switch_inline_query_current_chat='hw '
        ))
        kb.add(types.InlineKeyboardButton(
            text=l.f('general_back'), callback_data='menu:None'
        ))

    # back button
    else:
        kb.add(types.InlineKeyboardButton(
            text=l.f('general_back'), callback_data='menu:None'
        ))

    return kb


# handling button presses

@dp.callback_query(F.data == 'remotetype')
async def change_remote_type(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # changing type
    mg.change_remote_type(user.id)
    await call.answer()


@dp.callback_query(F.data == 'daydream')
async def start_daydream(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)

    out = mg.check_remote(user.id, daydream=True)
    if out != True: return await call.answer(l.f(out))

    # daydreaming
    remote = mg.remotes[call.from_user.id]
    remote.switch_daydreaming()
    await call.answer()


@dp.callback_query(F.data.startswith('itemaction:'))
async def item_action(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)
    args = call.data.split(':')

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # getting item
    remote = mg.remotes[call.from_user.id]
    inv = mg.get_inventory(user)
    item = [i for i in inv if i.key == remote.inv_selected]
    if len(item) == 0:
        return await call.answer(l.f('callback_err_remote_no_item_selected'))
    item = item[0]

    # eating
    if args[1] == 'eat':
        if not item.item.food:
            return await call.answer(l.f('callback_err_remote_not_edible'))
        
        mg.eat_item(user, item)
        return await call.answer(user.get_energy_pb())

    await call.answer()


@dp.callback_query(F.data == 'makehwitem')
async def make_hw_item(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # getting recipe
    remote = mg.remotes[call.from_user.id]
    if remote.hw_item == None:
        return await call.answer(l.f('callback_err_remote_no_item_selected'))

    out = mg.make_item(user, mg.recipe.data[remote.hw_item])
    if out:
        return await call.answer(l.f(out))
    await call.answer()


@dp.callback_query(F.data.startswith('menu:'))
async def change_remote_type(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)
    args = call.data.split(':')

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # changing menu
    menu = args[1] if args[1] != 'None' else None
    remote = mg.remotes[call.from_user.id]
    remote.menu = menu
    remote.changed = True
    remote.reset_data()
    await call.answer()


@dp.callback_query(F.data.startswith('selectitem:'))
async def inv_select_item(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)
    args = call.data.split(':')

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # selecting item
    remote = mg.remotes[call.from_user.id]
    remote.inv_selected = None if args[1] == remote.inv_selected else args[1]
    remote.changed = True
    await call.answer()


@dp.callback_query(F.data == 'logout')
async def logout_player(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)

    out = mg.check_remote(user.id, False)
    if out != True: return await call.answer(l.f(out))

    # logging out
    mg.remotes[user.id].running = False
    await call.answer()


@dp.callback_query(F.data.startswith('move:'))
async def move_player(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)
    args = call.data.split(':')

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # moving
    x = int(args[1])
    y = int(args[2])

    out = mg.move(call.from_user.id, x, y)
    if out: return await call.answer(l.f(out))

    await call.answer()


@dp.callback_query(F.data.startswith('break:'))
async def break_object(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)
    args = call.data.split(':')

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # breaking
    x = int(args[1])
    y = int(args[2])

    out = mg.destroy(call.from_user.id, x, y)
    if out: return await call.answer(l.f(out))

    await call.answer()


@dp.callback_query(F.data.startswith('place:'))
async def place_object(call: types.callback_query):
    user = mg.get_user(call.from_user)
    l = mg.get_locale(user.lang)
    args = call.data.split(':')

    out = mg.check_remote(user.id)
    if out != True: return await call.answer(l.f(out))

    # breaking
    x = int(args[1])
    y = int(args[2])

    out = mg.place(call.from_user.id, x, y)
    if out: return await call.answer(l.f(out))

    await call.answer()


# remote loop

async def run_remote_cycle(userid: int):
    '''
    Starts the remote cycle.
    '''
    remote = mg.remotes[userid]
    msg = remote.message
    user = mg.get_user(userid)

    while remote.running:
        # closing remote if too much time passed
        l = mg.get_locale(user.lang)

        if time.time()-remote.last_activity > MAX_AFK_TIME_SECONDS:
            remote.running = False
            break

        # waiting until editing message
        await asyncio.sleep(1.1)
        mg.remote_tick(user, remote)

        # getting new message contents
        newtext = get_remote_text(l, remote, user)
        if newtext != remote.prev_text:
            remote.prev_text = newtext
            remote.changed = True

        keyboard = get_remote_kb(l, remote, user)

        # editing message
        if remote.changed:
            remote.changed = False
            try:
                await msg.edit_text(text=newtext, reply_markup=keyboard.as_markup())
            except Exception as e:
                log(e, level=ERROR)

        remote.performed_action = False

    # deleting remote message
    mg.broadcast_user('chat_user_left', userid)
    log(f'{user.game_name} ({user.id}) logged out...')
    await msg.delete()


# commands

@dp.message(Command('login'))
async def remote(msg: types.Message):
    '''
    starts a remote.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    if msg.chat.type != 'private':
        await msg.reply(l.f('err_remote_not_private'))
        return
    elif user.id in mg.remotes:
        await msg.reply(l.f('err_remote_exists'))
        return
    
    # name not entered
    if user.game_name == None:
        kb = InlineKeyboardBuilder()
        kb.add(types.InlineKeyboardButton(
            text=l.f('btn_remote_choose_name'), switch_inline_query_current_chat='name '
        ))
        await msg.reply(l.f('remote_name_enter'), reply_markup=kb.as_markup())
        return

    # starting remote cycle
    mg.remotes[msg.from_user.id] = api.Remote(None, msg.from_user.id)
    await msg.delete()
    botmsg = await bot.send_message(msg.chat.id, l.f('general_loading'))
    log(f'{user.game_name} ({user.id}) logged in!')

    mg.remotes[msg.from_user.id].message = botmsg
    mg.broadcast_user('chat_user_joined', msg.from_user.id)
    try:
        await run_remote_cycle(msg.from_user.id)
    except Exception as e:
        mg.broadcast_user('chat_user_left', msg.from_user.id)
        log(f'{user.game_name} ({user.id}) logged out due to an error: {e}', level=ERROR)
        await botmsg.edit_text(l.f(f'remote_error', error=e))

    del mg.remotes[msg.from_user.id]


@dp.message(Command('status'))
async def status(msg: types.Message):
    '''
    shows server status.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    if user.id in mg.remotes:
        await msg.delete()
        return

    await msg.reply(get_server_status_text(l))


@dp.message(Command('logout'))
async def logout(msg: types.Message):
    '''
    quit the world.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    if user.id not in mg.remotes:
        await msg.reply(l.f('err_logout_no_remote'))
        return
    
    mg.remotes[user.id].running = False
    await msg.delete()


@dp.message()
async def ingamechat(msg: types.Message):
    '''
    ingame chat.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    if msg.text == None or len(msg.text) == 0: return
    if msg.text.startswith('/'): return
    if msg.from_user.id not in mg.remotes: return

    await msg.delete()

    if msg.text.startswith(l.f('@')): return
    remote = mg.remotes[msg.from_user.id]
    if remote.daydreaming: return

    mg.send_to_chat(l, user.id, msg.text)