#!/usr/bin/env python3
"""Render the verified 4-case eligibility demo as an animated terminal GIF.

The lines below are the real output captured in DEMO.md (from a live local-devnet
run of prove-eligibility.ts). This just replays them in a styled terminal so the
result is easy to see at a glance. Regenerate with:

    python3 scripts/make-demo-gif.py
"""
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SIZE = 17
LH = 27           # line height
PAD_X = 26
TITLE_H = 44
TOP = 14
BOT = 16
W = 960

BG = (13, 17, 23)
TITLEBG = (22, 27, 34)
DOTS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]
COL = {
    "text":   (201, 209, 217),
    "dim":    (110, 118, 129),
    "prompt": (88, 166, 255),
    "ok":     (63, 185, 80),
    "bad":    (248, 81, 73),
    "blank":  (201, 209, 217),
}

# (style, text)  — real output, hashes shortened for readability
LINES = [
    ("prompt", "$ npm run prove -- --network undeployed      # age 20, under the cap"),
    ("dim",    "  public criteria (on-chain):    minAge=18   maxPriorFunding=100000"),
    ("dim",    "  private witnesses (never sent): age=20      priorFunding=0"),
    ("text",   "  deploying eligibility contract ..."),
    ("text",   "  contract: 460870b0…a568a2d5"),
    ("text",   "  generating ZK proof (proof server) ..."),
    ("ok",     "  ✓ ELIGIBLE — proof verified; age never left the client"),
    ("dim",    "    audit ref: 460870b0…@005aa3a8…"),
    ("blank",  ""),
    ("prompt", "$ …  REPLAY=1  …            # same applicant proves twice"),
    ("ok",     "  ✓ REPLAY BLOCKED — nullifier already spent"),
    ("blank",  ""),
    ("prompt", "$ …  AGE=16  …              # under the minimum age"),
    ("bad",    "  ✗ INELIGIBLE — applicant below minimum age"),
    ("blank",  ""),
    ("prompt", "$ …  FUNDING=200000  …      # over the prior-funding cap"),
    ("bad",    "  ✗ INELIGIBLE — applicant exceeds prior-funding cap"),
]

font = ImageFont.truetype(FONT, SIZE)
font_b = ImageFont.truetype(FONT_B, SIZE)
H = TITLE_H + TOP + LH * len(LINES) + BOT


def frame(n):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TITLE_H], fill=TITLEBG)
    for i, c in enumerate(DOTS):
        d.ellipse([20 + i * 24, 15, 34 + i * 24, 29], fill=c)
    d.text((W // 2, TITLE_H // 2), "NAWA × Midnight — private eligibility proof",
           font=font, fill=(139, 148, 158), anchor="mm")
    y = TITLE_H + TOP
    for style, text in LINES[:n]:
        bold = style in ("ok", "bad", "prompt")
        d.text((PAD_X, y), text, font=(font_b if bold else font), fill=COL[style])
        y += LH
    return img


frames, durations = [], []
for n in range(1, len(LINES) + 1):
    style = LINES[n - 1][0]
    if style == "blank":
        continue
    frames.append(frame(n))
    durations.append(950 if style in ("ok", "bad") else 340)
# final hold
frames.append(frame(len(LINES)))
durations.append(3000)

out = "docs/demo.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations,
               loop=0, optimize=True, disposal=2)
print(f"wrote {out}  ({len(frames)} frames, {W}x{H})")
