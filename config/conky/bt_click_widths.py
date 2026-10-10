#!/usr/bin/python3
"""Measure the inline name and status in the widget's current fonts."""
import math
import sys
import hashlib
from pathlib import Path
cache_dir = Path.home() / '.cache' / 'conky-bt-widths'
cache_dir.mkdir(exist_ok=True)
cache = cache_dir / hashlib.sha256(('v1|' + '|'.join(sys.argv[1:])).encode()).hexdigest()
if cache.exists():
    print(cache.read_text().strip())
    sys.exit(0)
from PIL import ImageFont
name_font = ImageFont.truetype("DejaVuSans.ttf", 18)
status_font = ImageFont.truetype("DejaVuSans.ttf", 12)
name_end = 4 + name_font.getlength(sys.argv[1])
word_start = name_end + name_font.getlength(" ") + status_font.getlength("• ")
status = "connected" if sys.argv[2] == "1" else "disconnected"
result = f'{math.floor(word_start)} {math.ceil(word_start + status_font.getlength(status))} {math.ceil(name_end)}'
cache.write_text(result)
print(result)
