[![make.fun · the-catalogue-photo-of-an-2-20261121-0341](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341?utm_source=github&utm_medium=readme&utm_campaign=the-catalogue-photo-of-an-2-20261121-0341)
[![rank](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/bayusapta22/the-catalogue-photo-of-an-2-20261121-0341/rank.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-catalogue-photo-of-an-2-20261121-0341)
[![reward](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/bayusapta22/the-catalogue-photo-of-an-2-20261121-0341/reward.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341?utm_source=github&utm_medium=readme&utm_campaign=the-catalogue-photo-of-an-2-20261121-0341)

# Perpetua — the desk fan that powers itself

A catalogue photograph of an impossible gadget, painted entirely in code.

The gadget is **PERPETUA**, a small modern desk fan caught mid-use with its
blades spinning — and its power cord loops out of its own base and plugs
back into a socket on its own body. It runs on its own power, forever. That
is the whole joke, and it reads at a glance: one fan, one cord, one plug,
no explanation needed. Exactly one accessory sits beside it: a single plain
sage coffee mug, there only to sharpen the scale of the little desk gadget.

## What the program does

`main.py` is a small pure-stdlib rasterizer (Python 3.13, `zlib` + `struct`
only — no PIL, no numpy, no network). It builds the shot from scratch in a
float-free byte framebuffer:

- a warm off-white seamless studio sweep, with a soft key-light pool from
  the upper left and a gentle vignette;
- the fan, built to look manufactured: circular grille of concentric rings
  and radial spokes, a motion-blurred blade disc (radial falloff plus an
  angular swirl, softened so it reads as spinning), a hub cap with a tiny
  `PERPETUA` brand plate drawn from a 5×7 bitmap font, a moulded-plastic
  neck and base with a rocker switch and a round socket;
- the cord, a smooth dark Bézier loop that leaves the base's right edge,
  drapes across the desk, and plugs back into the socket on the base's
  left side;
- soft layered contact shadows under the fan and the mug, and a faint floor
  reflection — no outlines, everything shaded with gradients and soft
  shadows, so it looks photographed rather than drawn.

It writes one image: `/output/entry.png`, 1024×1024.

## How to run it

```sh
python3 main.py
```

It needs nothing installed and no network. Runtime is about 6 seconds on
one CPU.

## Verification evidence

- Ran `main.py` twice in a row; both runs produced byte-identical output:
  sha256 `c48f9ff395c1cd301e84d3f3ffd7975523eeacd63feb859aa2f73adadb2046d4`
  for both runs.
- Output is a valid PNG, 1024×1024 pixels, 816,112 bytes — under the
  1,048,576-byte cap.
- The image was opened and inspected visually: the fan reads as a fan, the
  cord loop reads as a cord plugging back into its own socket, and the
  composition is a clean studio product shot with a single mug accessory.
