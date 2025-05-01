
import json
import random
import pygame as pg
from typing import *
import os

pg.init()


# drawing functions

changed = True

def draw(rect: pg.Rect, item: str = None):
    global changed

    if item == None:
        item = list(obj.keys())[selected]

    if pg.key.get_pressed()[pg.K_SPACE]:
        item = None
    
    for x in range(rect.left, rect.right):
        if x >= size[0] or x < 0: continue
        for y in range(rect.top, rect.bottom):
            if y >= size[1] or y < 0: continue
            drawn[y][x] = item

    pg.draw.rect(surface, obj[item], rect)
    changed = True


# reading objects

obj: Dict[str, Tuple[int,int,int]] = {None: [0,0,0]}
selected: int = 0 

with open('data.json', encoding='utf-8') as f:
    data = json.load(f)
    data = data['obj']
    for k, v in data.items():
        obj[k] = v['color']


# reading map

filename = input(f'Enter the filename to open a map > ')

if not os.path.exists('maps/'):
    os.mkdir('maps/')

if not os.path.exists(f'maps/{filename}.map'):
    print('Creating a new map...')
    
    chunks = [
        int(input(f'Enter X chunk amount > ')),
        int(input(f'Enter Y chunk amount > '))
    ]
    chunk_size = 64
    size = [chunks[0]*chunk_size, chunks[1]*chunk_size]
    drawn: List[List[str]] = [[None for _ in range(size[0])] for _ in range(size[1])]

    surface = pg.Surface(size)
    surface.fill((0,0,0))

else:
    print('Opening map...')

    with open(f'maps/{filename}.map') as f:
        data = f.read()

    rows = data.split('\n')
    size = [len(rows[0].split(';')), len(rows)]
    drawn = []

    for i in rows:
        row = i.split(';')
        drawn.append([ None if i == '-' else i for i in row])

    # drawing map
    surface = pg.Surface(size)
    surface.fill((0,0,0))

    for y, row in enumerate(drawn):
        for x, i in enumerate(row):
            if i == None: continue
            selected = list(obj.keys()).index(i)
            draw(pg.Rect(x, y, 1, 1))



# other stuff

offset = [0,0]
zoom = 1
pensize = 1

window = pg.display.set_mode((1280,720))
running = True


print('''
Use LMB to draw
Use LMB + Space to erase
Use E to export
Use S to save
Use Shift + Mouse wheel to change object
Use Mouse wheel to change pen size
Use Ctrl + Mouse wheel to zoom
Use 1, 2 to change tools
Use Alt + Mouse wheel to change spray speed
Hold Q while scrolling to increase scroll speed
''')


emojis = ['✏', '✒']
tool = 0

spray = 0.00
spraytime = 0.1
tile = [0,0]


# saving function

def export():
    if not os.path.exists('map/'):
        os.mkdir('map/')
    else:
        print('Map directory already exists. Delete it to save')
        return

    yoffset = 0
    count = 0
    total = chunks[0]*chunks[1]

    for y in range(chunks[1]):
        xoffset = 0

        if not os.path.exists(f'map/{y}/'):
            os.mkdir(f'map/{y}/')

        for x in range(chunks[0]):
            l = []
            for y1 in range(chunk_size):
                l.append(drawn[yoffset+y1][xoffset:xoffset+chunk_size])

            with open(f'map/{y}/{x}.chunk', 'w') as f:
                out = '\n'.join( [';'.join( [it if it != None else '-' for it in yrow] ) for yrow in l] )
                f.write(out)

            count += 1
            xoffset += chunk_size
            print(f'Writing... {count} / {total}', end='\r', flush=True)

        yoffset += chunk_size
    
    print('\nExported!')


def save():
    with open(f'maps/{filename}.map', 'w') as f:
        out = '\n'.join( [';'.join( [it if it != None else '-' for it in yrow] ) for yrow in drawn] )
        f.write(out)
    
    print('Saved!')


# title updating

def update_title():
    text = f'{emojis[tool]} ({spraytime}) | ({selected+1} / {len(obj)}) {list(obj.items())[selected][0]}'
    text += f'    {tile}'
    pg.display.set_caption(text)

update_title()


# main loop 

while running:
    window.fill((20,20,20))

    # mouse pos
    mouse_pos = pg.mouse.get_pos() # mouse pos relative to the topleft of the window
    tile = [
        max(0, min(int((mouse_pos[0]-offset[0])/zoom), size[0]-1)),
        max(0, min(int((mouse_pos[1]-offset[1])/zoom), size[1]-1))
    ]

    # events
    events = pg.event.get()

    for event in events:
        # quitting the game
        if event.type == pg.QUIT:
            running = False

        # saving
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_s:
                try:
                    save()
                except Exception as e:
                    print(f'Error while saving: {e}')

            if event.key == pg.K_e:
                try:
                    export()
                except Exception as e:
                    print(f'Error while exporting: {e}')

            if event.unicode in ['1', '2']:
                tool = int(event.unicode)-1
                update_title()

        # zoom
        if event.type == pg.MOUSEWHEEL:
            if pg.key.get_pressed()[pg.K_LCTRL]:
                zoom = max(1, zoom+event.y)
                changed = True

            elif pg.key.get_pressed()[pg.K_LSHIFT]:
                selected += int(event.y)
                if selected < 0: selected = len(obj)
                if selected >= len(obj): selected = 0
                update_title()

            elif pg.key.get_pressed()[pg.K_LALT]:
                spraytime += event.y*0.01*(int(pg.key.get_pressed()[pg.K_q])*99+1)
                if spraytime < 0.01:
                    spraytime = 0.01
                spraytime = round(spraytime, 3)
                update_title()
            
            else:
                pensize += event.y*(int(pg.key.get_pressed()[pg.K_q])*10+1)
                if pensize <= 0:
                    pensize = 1
                if pensize > size[0] or pensize > size[1]:
                    pensize = min(size[0], size[1])

        # moving cam
        if event.type == pg.MOUSEMOTION:
            if pg.mouse.get_pressed()[1]:
                offset[0] += event.rel[0]
                offset[1] += event.rel[1]
                changed = True
            update_title()

    # drawing
    s = pensize*2-1

    if pg.mouse.get_pressed(3)[0]:
        # solid pen
        if tool == 0:
            rect = pg.Rect((tile[0]-pensize+1), (tile[1]-pensize+1), s,s)
            draw(rect)

        # airbrush
        elif tool == 1:
            spray -= 1
            boundary = pg.Rect((tile[0]-pensize+1), (tile[1]-pensize+1), s,s)

            while spray <= 0.0:
                rect = pg.Rect(
                    random.randint(boundary.left, boundary.right),
                    random.randint(boundary.top, boundary.bottom),
                    1,1
                )
                draw(rect)
                spray += spraytime

        # water
        # elif tool == 2:
        #     spray -= 1
            
        #     for i in range(4):
        #         cursize = pensize+(4-i)
        #         s = cursize*2-1

        #         rect = pg.Rect((tile[0]-cursize+1), (tile[1]-cursize+1), s,s)
        #         draw(rect, f'water{i+1}')


    # displaying
    if changed:
        scr = pg.Surface((int(1280/zoom), int(720/zoom)))
        scr.fill((20,20,20))
        scr.blit(surface, (offset[0]/zoom, offset[1]/zoom))
        scaled = pg.transform.scale_by(scr, zoom)
        changed = False

    window.blit(scaled, (0,0))

    rect = pg.Rect(
        (tile[0]-pensize+1)*zoom+int(offset[0]/zoom)*zoom,
        (tile[1]-pensize+1)*zoom+int(offset[1]/zoom)*zoom,
        zoom*s,zoom*s
    )
    pg.draw.rect(window, (255,255,255), rect, 1)

    pg.display.flip()
