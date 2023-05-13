# Generate the HTML page with cards for printing.

import pickle, sys, os, math, random
from collections import defaultdict
from PIL import Image

output_dir = sys.argv[1]
cardsets = sys.argv[2:]

# Load & filter down to the used ones
allcards = []
perset = defaultdict(int)
for i, cardset in enumerate(cardsets):
    with open(cardset, 'rb') as f:
        state = pickle.load(f)
    for k, v in state.items():
        if not v['use']:
            continue
        v['set'] = i
        allcards.append(v)
        perset[i] += 1
print(len(allcards), 'cards')
ROWS, COLS = 5, 3
print(math.ceil(len(allcards)/(ROWS*COLS)), 'sheets')

# Assign IDs
TARGET_PER_SET = 500
random.seed(42)
offset = 0
idx = 1
for i, setcnt in perset.items():
    assert idx < TARGET_PER_SET * (i + 1)
    for j in range(setcnt):
        # Assign ID to the card at index [offset]
        # It is j-th in the current set i, should be at least idx+1.
        # Aim for (remaining cards) / (remaining range) to span the range.
        # Maximum = target * 1.5
        # => Simple uniform random for something inbetween.
        left_in_range = (TARGET_PER_SET * (i+1) - idx - 1)
        target_step = left_in_range // (setcnt - j)
        step = random.randint(1, min(left_in_range, int(1.5*target_step)))
        idx += step
        allcards[offset]['idx'] = idx
        offset += 1
print('set: count / first id / last id')
offset = 0
for i, setcnt in perset.items():
    print('{} {} {} {}'.format(
        i,
        setcnt,
        allcards[offset]['idx'],
        allcards[offset + setcnt - 1]['idx'],
    ))
    offset += setcnt
# sanity check, this is the point of the game, don't fuck it up
lastid = 0
for card in allcards:
    assert card['idx'] >= lastid + 1
    lastid = card['idx']

result = """
<html>
<head>
    <style>
        @page {
            margin: 0;
            size: A4 portrait;
        }

        * {
            padding: 0;
            margin: 0;
            border: 0;
        }

        .cut-outline {
            width: 70mm;
            height: 54mm;
            position: absolute;
            display: block;
            border-bottom: 1px dashed black;
        }

        .front {
            border-right: 1px dashed black;
        }

        .back {
            border-left: 1px dashed black;
        }

        .card {
            width: 67mm;
            height: 50mm;
            border: 1px solid gray;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            position: absolute;
        }

        img {
            width: 100%;
        }

        .text {
            display: block;
            width: 65mm;
            padding: 1mm 1mm;
            font-size: 13pt;
        }

        .number {
            width: 1cm;
            height: 1cm;
            border-radius: 50%;
            background: white;
            display: flex;
            justify-content: center;
            align-items:center;
            font-weight: bold;
            border: 1px solid black;
            
            position: relative;
            float: right;
            margin-top: -5mm;
            margin-right: 2mm;
            z-index: 1000;
        }

        .series {
            width: 0.6cm;
            height: 0.6cm;
            border-radius: 50%;
            background: white;
            display: flex;
            justify-content: center;
            align-items:center;
            font-size: 10pt;
            border: 1px solid black;
            position: absolute;
            top: 1mm;
            left: 1mm;
        }

        .page {
            page-break-after: always;
            
            position: relative;
            /* lol go home css you are drunk https://stackoverflow.com/a/41176134 */
            border: 1px solid white;
        }
    </style>
</head>

<body>
"""

for i in range(0, len(allcards), ROWS*COLS):
    pagecards = allcards[i:i+ROWS*COLS]
    
    # Convert
    for card in pagecards:
        s, frame = card['set'], card['frame']
        imgpath = os.path.join(output_dir, f'set{s}_frame{frame}.jpg')
        if not os.path.exists(imgpath):
            inpath = os.path.join(os.path.dirname(cardsets[s]), f'tmp/frame{frame}.png')
            im = Image.open(inpath)
            im.convert('RGB')
            im.save(imgpath)
        

    # First page.
    result += '<div class="page">'
    for j, card in enumerate(pagecards):
        s, frame = card['set'], card['frame']
        text = card['text']
        pos = 'left: {}mm; top: {}mm;'.format(70*(j%COLS), 55*(j//COLS))
        result += f"""
        <div class="cut-outline front" style="{pos}">
            <div class="card">
                <img src="set{s}_frame{frame}.jpg" />
                <span class="text">{text}</span>
            </div>
        </div>"""
    result += '</div>'

    # Second page.
    result += '<div class="page">'
    # Have to go in the other order
    for j in range(len(pagecards)):
        row = j // COLS
        col = COLS - 1 - (j % COLS)
        k = row*COLS + (j % COLS)
        if k >= len(pagecards):
            result += '<div class="cut-outline">'
            continue
        card = pagecards[k]

        s, frame = card['set'], card['frame']
        sroman = ['I', 'II', 'III', 'IV'][s] # todo more when this crashes :)
        text = card['text']
        number = card['idx']
        pos = 'left: {}mm; top: {}mm;'.format(70*col, 55*row)
        result += f"""
        <div class="cut-outline back" style="{pos}">
            <div class="card">
                <img src="set{s}_frame{frame}.jpg" />
                <span class="series">{sroman}</span>
                <span class="number">{number}</span>
                <span class="text">{text}</span>
            </div>
        </div>"""
    result += '</div>'


result += """
    </div>
</body>
</html>
"""

with open(os.path.join(output_dir, 'cards.html') , 'w') as f:
    f.write(result)