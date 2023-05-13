# The GUI tool to prepare cards.

import sys

video_path = sys.argv[1]
subs_path = sys.argv[2]
state_file = './state.pickle'
tmp_dir = './tmp'

# Extract stuff from input files
import pysrt, ffmpeg, os, time
from PIL import Image
subs = pysrt.open(subs_path)

# Get random frame to figure out the picture size...
test_frame_path = f'{tmp_dir}/testframe.png'
ffmpeg.input(video_path, ss=0).output(test_frame_path, vframes=1).overwrite_output().run()
image_size = None
with Image.open(test_frame_path) as im:
    image_size = im.size

# State management
import pickle
STATE = None
try:
    STATE = pickle.load(open(state_file, 'rb'))
except:
    print('Loading state failed')
# Bootstrap new state
def defaulttext(text):
    lines = text.split('\n')
    if all(line.startswith('- ') for line in lines):
        return '\n'.join('"' + line[2:] + '"' for line in lines)
    return text.replace('\n', ' ')
if not STATE:
    STATE = {
        i : {
            'use': False,
            'text': defaulttext(subs[i].text),
            'frame': (subs[i].start.ordinal + subs[i].end.ordinal) // 2,
        }
        for i in range(len(subs))
    }

# GUI layout setup
import PySimpleGUI as sg
import textwrap

KEY_STATS_TEXT = 'key-stats-text'
KEY_SUB_LIST = 'key-sub-list'
KEY_SELECTED_INFO = 'key-selected-info'
KEY_SELECTED_USE = 'key-selected-use'
KEY_FRAME_IMAGE = 'key-frame-image'
KEY_SELECTED_TEXT = 'key-selected-text'
KEY_SAVE_BUTTON = 'key-save-button'
KEY_FRAME_PREV2 = 'key-frame-prev2'
KEY_FRAME_PREV = 'key-frame-prev'
KEY_FRAME_MID = 'key-frame-mid'
KEY_FRAME_NEXT = 'key-frame-next'
KEY_FRAME_NEXT2 = 'key-frame-next2'

col_left = sg.Column([
    [
        sg.Frame('Stats', [[sg.Text('placeholder', key=KEY_STATS_TEXT)]]),
        sg.Frame('Save', [[sg.Button('saved', key=KEY_SAVE_BUTTON, enable_events=True, font=('Arial', 30))]])
    ],
    [sg.Listbox(values=[], key=KEY_SUB_LIST, enable_events=True, size=(75, 75))],
    [sg.Frame('Hotkeys', [
        [sg.Text(textwrap.dedent('''
        Ctrl+S: Save changes
        
        Ctrl+Up/Down: Change subtitle
        
        Ctrl+Enter: Toggle use
        Ctrl+T: Focus text edit
        
        Ctrl+Left/Right: Advance one frame
        Ctrl+Shift+Left/Right: Advance one second
        Ctrl+M: Reset frame to middle
        ...
        '''))]
    ])],
])
col_right = sg.Column([
    [sg.Frame('Selection', [
        [sg.Text('(select something)', font=('Arial', 25), key=KEY_SELECTED_INFO)],
        [sg.Button('Use?', font=('Arial', 15), key=KEY_SELECTED_USE, enable_events=True)],
        [sg.Image(test_frame_path, size=image_size, key=KEY_FRAME_IMAGE)],
        [
            sg.Button('<<', key=KEY_FRAME_PREV2, enable_events=True),
            sg.Button('<', key=KEY_FRAME_PREV, enable_events=True),
            sg.Button('mid', key=KEY_FRAME_MID, enable_events=True),
            sg.Button('>', key=KEY_FRAME_NEXT, enable_events=True),
            sg.Button('>>', key=KEY_FRAME_NEXT2, enable_events=True),
        ],
        [sg.Multiline('...', size=(60, 3), font=('Arial', 20), key=KEY_SELECTED_TEXT, change_submits=True)],
    ])],
])
layout = [[col_left, col_right]]
window = sg.Window('Timeline', layout, margins=(25, 25))

# Helpers for GUI
class TextWithLabel:
  def __init__(self, label, text):
    self.label = label
    self.text = text
  def __str__(self):
    return self.text

import math
def frame_to_timestamp(f):
    seconds = math.floor(f / 1000)
    frac = f - seconds*1000
    hours = math.floor(seconds / 3600)
    minutes = math.floor((seconds % 3600)/ 60)
    seconds = seconds % 60
    return f'{hours:02}:{minutes:02}:{seconds:02}.{frac:03}'

# Event handlers / helpers
STATE_SELECTED = None
LIST_ITEMS = []
def update_frame_counter(i):
    global STATE_SELECTED, LIST_ITEMS
    frame = STATE[i]['frame']
    timestamp = frame_to_timestamp(frame)
    frame_text = f'#{i} frame: {timestamp} ({frame})'
    warning = ''
    if frame < subs[i].start.ordinal:
        warning = 'BEFORE START'
    elif frame > subs[i].end.ordinal:
        warning = 'AFTER END'
    window[KEY_SELECTED_INFO].update(f'{frame_text} {warning}', text_color='red' if warning else 'black')

def sub_selected(i):
    global STATE_SELECTED, LIST_ITEMS
    STATE_SELECTED = i
    update_frame_counter(i)
    window[KEY_SELECTED_USE].update('Use? Yes' if STATE[i]['use'] else 'Use? No', button_color='green' if STATE[i]['use'] else 'gray')
    window[KEY_SUB_LIST].update(LIST_ITEMS, set_to_index=i, scroll_to_index=max(0, i-20))
    window[KEY_SELECTED_TEXT].update(STATE[i]['text'])
    update_image(STATE[i]['frame'])

# This blocks the UI thread but it is simple.
def update_image(frame):
    path = f'{tmp_dir}/frame{frame}.png'
    if not os.path.exists(path):
        ffmpeg.input(video_path, ss=frame/1000.0).output(path, vframes=1).overwrite_output().run()
    window[KEY_FRAME_IMAGE].update(path)

DIRTY = False
def state_changed(i):
    global STATE, LIST_ITEMS, DIRTY
    DIRTY = True
    sub = STATE[i]
    text = sub['text']
    used = '✓' if sub['use'] else '   '
    LIST_ITEMS[i] = TextWithLabel(i, f'{used} #{i} {text}')
    window[KEY_SUB_LIST].update(LIST_ITEMS, set_to_index=i, scroll_to_index=max(0, i-20))
    window[KEY_SAVE_BUTTON].update('SAVE?', button_color='red')

def toggle_use():
    global STATE, STATE_SELECTED
    STATE[STATE_SELECTED]['use'] = not STATE[STATE_SELECTED]['use']
    sub_selected(STATE_SELECTED)
    state_changed(STATE_SELECTED)

def text_changed(text):
    global STATE, STATE_SELECTED
    STATE[STATE_SELECTED]['text'] = text
    state_changed(STATE_SELECTED)

def set_frame_mid():
    global STATE, STATE_SELECTED
    sub = subs[STATE_SELECTED]
    STATE[STATE_SELECTED]['frame'] = (sub.start.ordinal + sub.end.ordinal) // 2
    state_changed(STATE_SELECTED)
    update_image(STATE[STATE_SELECTED]['frame'])
    update_frame_counter(STATE_SELECTED)

def set_frame_relative(offset):
    global STATE, STATE_SELECTED
    sub = subs[STATE_SELECTED]
    STATE[STATE_SELECTED]['frame'] += offset
    state_changed(STATE_SELECTED)
    update_image(STATE[STATE_SELECTED]['frame'])
    update_frame_counter(STATE_SELECTED)

def update_stats():
    global STATE
    total = len(STATE)
    used = len([i for i, sub in STATE.items() if sub['use']])
    window[KEY_STATS_TEXT].update(f'Using {used}/{total}')

def save():
    global STATE, DIRTY
    DIRTY = False
    backup_path = state_file + '.bckp-' + str(int(time.time()))
    if os.path.exists(state_file):
        print('Backup dumped to:', backup_path)
        os.rename(state_file, backup_path)
    with open(state_file, 'wb') as f:
        pickle.dump(STATE, f)   
    window[KEY_SAVE_BUTTON].update('saved', button_color='gray')

# Init from STATE
for i, sub in STATE.items():
    text = sub['text']
    used = '✓' if sub['use'] else '   '
    LIST_ITEMS.append(TextWithLabel(i, f'{used} #{i} {text}'))
    window[KEY_SUB_LIST].Values.append(LIST_ITEMS[i])

# Hotkey setup
window.finalize()
window.bind('<Control-Up>', 'bind-up')
window.bind('<Control-Down>', 'bind-down')
window.bind('<Control-Return>', KEY_SELECTED_USE)
window.bind('<Control_L>s', KEY_SAVE_BUTTON)
window.bind('<Control_L>t', 'bind-focus-text')
window.bind('<Control-Left>', KEY_FRAME_PREV)
window.bind('<Control-Right>', KEY_FRAME_NEXT)
window.bind('<Control-Shift-Left>', KEY_FRAME_PREV2)
window.bind('<Control-Shift-Right>', KEY_FRAME_NEXT2)
window.bind('<Control-M>', KEY_FRAME_MID)
# Bootstrap
sub_selected(0)

# Event loop
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    update_stats() # Not really efficient but whatever
    print(event, values)
    if event == KEY_SUB_LIST:
        sub_selected(values[KEY_SUB_LIST][0].label)
    elif event == KEY_SELECTED_USE:
        toggle_use()
    elif event == 'bind-up' and STATE_SELECTED > 0:
        sub_selected(STATE_SELECTED - 1)
    elif event == 'bind-down' and STATE_SELECTED + 1 < len(STATE):
        sub_selected(STATE_SELECTED + 1)
    elif event == KEY_SELECTED_TEXT:
        text_changed(values[KEY_SELECTED_TEXT])
    elif event == KEY_SAVE_BUTTON:
        save()
    elif event == 'bind-focus-text':
        window[KEY_SELECTED_TEXT].set_focus()
    elif event == KEY_FRAME_MID:
        set_frame_mid()
    elif event == KEY_FRAME_NEXT:
        set_frame_relative(42)
    elif event == KEY_FRAME_NEXT2:
        set_frame_relative(1000)
    elif event == KEY_FRAME_PREV:
        set_frame_relative(-42)
    elif event == KEY_FRAME_PREV2:
        set_frame_relative(-1000)

window.close()