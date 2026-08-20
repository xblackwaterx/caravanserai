"""Build assets/demo.gif from a real captured terminal session.

Uses pyte (a real terminal emulator) to compute the exact correct screen
grid at each step - no black-box SVG animation engine to get wrong. Renders
each frame as a PNG via Pillow, then assembles a GIF with per-frame delays
matching the real captured timestamps (capped so it doesn't run 11s dead
air per loop).

Run: python scripts/build_demo_gif.py
Requires: pip install pyte pillow (dev-only, not a package dependency).
"""
import json

import pyte
from PIL import Image, ImageDraw, ImageFont

COLS, ROWS = 62, 14
FONT_SIZE = 16
CHAR_W, CHAR_H = 10, 20
PADDING = 16
BG = (40, 44, 52)
FG = (185, 192, 203)

with open("capture_events.json") as f:
    events = json.load(f)

screen = pyte.Screen(COLS, ROWS)
stream = pyte.ByteStream(screen)

try:
    font = ImageFont.truetype("consola.ttf", FONT_SIZE)
except OSError:
    font = ImageFont.load_default()


def render_frame(display_lines):
    w = COLS * CHAR_W + PADDING * 2
    h = ROWS * CHAR_H + PADDING * 2
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    for row, line in enumerate(display_lines):
        draw.text((PADDING, PADDING + row * CHAR_H), line, font=font, fill=FG)
    return img


frames = []
delays = []
prev_time = 0.0

for t, line in events:
    stream.feed(line.encode("utf-8"))
    frames.append(render_frame(screen.display))
    # cap each real delay so the crash pause / gap between runs doesn't
    # produce a multi-second frozen frame - clamp to a max of 700ms/frame
    delay_ms = min(int((t - prev_time) * 1000), 700)
    delays.append(max(delay_ms, 60))
    prev_time = t

# hold the final frame longer so "migration complete." is readable
delays[-1] = 2500

frames[0].save(
    "assets/demo.gif",
    save_all=True,
    append_images=frames[1:],
    duration=delays,
    loop=0,
    optimize=True,
)
print(f"wrote assets/demo.gif - {len(frames)} frames")
