# Make the GUI more responsive by pre-generating frame previews.
# Ideally the GUI would do so in a background thread, but that
# felt like too much work for a prototype :)

import ffmpeg
import pysrt
import os
import sys

video_path = sys.argv[1]
subs_path = sys.argv[2]

subs = pysrt.open(subs_path)
for i, sub in enumerate(subs):
    print(i, sub)
    mid = (sub.start.ordinal + sub.end.ordinal) // 2
    path = f'./tmp/frame{mid}.png'
    if os.path.exists(path):
        continue
    ffmpeg.input(video_path, ss=mid/1000.0).output(path, vframes=1).overwrite_output().run()