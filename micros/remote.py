
import asyncio
import random
import time
from typing import *

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
    print(q.result_id)
    if not q.result_id.startswith('namechange:'): return

    newname = q.result_id.removeprefix('namechange:')[:MAX_NAME_LENGTH]
    newname = utils.demarkup(newname)
    mg.change_game_name(q.from_user.id, newname)


@dp.inline_query()
async def inline(q: types.InlineQuery):
    user = mg.get_user(q.from_user.id)
    l = mg.get_locale(user.lang)

    query = q.query
    query1 = q.query.split(' ')

    if len(query1) > 0 and query1[0].lower() in [
        'name'
    ]:
        key = query1[0].lower()
        query = ' '.join(query1[1:])

    else:
        
        await q.answer([types.InlineQueryResultArticle(id='discard',
            title=l.f('inline_name_change_title'),
            input_message_content=types.InputTextMessageContent(
                message_text=l.f(f'inline_discard')
            )
        )], cache_time=5, is_personal=True)

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
                title=l.f('inline_name_change_entered_title', name=query),
                description=l.f('inline_name_change_entered_desc'),
                input_message_content=types.InputTextMessageContent(
                    message_text=l.f(f'inline_name_changed', name=utils.demarkup(query))
                )
            )

        await q.answer([button], cache_time=5, is_personal=True)
        return
    


# remote message

def get_remote_text(l: api.Locale, remote: api.Remote, user: api.User):
    '''
    Returns the text of the message.
    '''
    # minimap
    data = mg.map.get_rect_around(user.pos, 4)
    text = ''
    topleft = [user.pos[0]-4, user.pos[1]-4]
    overlay = mg.get_player_overlay(topleft, (9,9))

    for y, row in enumerate(data):
        outrow = ''

        for x, i in enumerate(row):
            if overlay[y][x] == None:
                outrow += mg.obj.get(i).emoji
            else:
                outrow += overlay[y][x]
    
        text += f'{outrow}\n'

    text = text[:-1]

    # remote timeout warning
    if time.time()-remote.last_activity > MAX_AFK_TIME_SECONDS-15:
        text += '\n\n'+l.f('remote_afk_warning', left=15)

    elif time.time()-remote.last_activity > MAX_AFK_TIME_SECONDS-30:
        text += '\n\n'+l.f('remote_afk_warning', left=30)

    return text


def get_remote_kb(l: api.Locale, remote: api.Remote, user: api.User) -> InlineKeyboardBuilder:
    '''
    Returns the keyboard of the message.
    '''
    kb = InlineKeyboardBuilder()

    # walking buttons
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
                text = mg.obj.get(item).button_text

            buttons.append(types.InlineKeyboardButton(
                text=text, callback_data=f'move:{x}:{y}'
            ))

        kb.row(*buttons)

    # options buttons
    kb.row(types.InlineKeyboardButton(
        text=l.f(f'button_remote_type_{user.remote}'), callback_data='remotetype'
    ))
    kb.add(types.InlineKeyboardButton(
        text=l.f('button_remote_logout'), callback_data='logout'
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
        await asyncio.sleep(1)

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
                print(e)

        remote.performed_action = False

    # deleting remote message
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
    await msg.delete()
    botmsg = await bot.send_message(msg.chat.id, l.f('general_loading'))

    mg.remotes[msg.from_user.id] = api.Remote(botmsg, msg.from_user.id)
    await run_remote_cycle(msg.from_user.id)
    del mg.remotes[msg.from_user.id]


@dp.message(Command('status'))
async def status(msg: types.Message):
    '''
    shows server status.
    '''
    user = mg.get_user(msg.from_user)
    l = mg.get_locale(user.lang)

    await msg.reply(l.f('status_text', online=len(mg.remotes)))