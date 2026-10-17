# Line 3 — evidence a worker can find again

The line's one thing is offline document search with exact source line citations.
The first working piece is [Evidence Search](tools/evidence-search/README.md):

```sh
python3 -B line-3/tools/evidence-search/search.py demo
```

It finds ZTO metadata from a bundled real Ethereum observation, with ranked
excerpts, line ranges, and hashes rechecked against the source files. Twelve
behavioral tests passed, and the two documented demo queries returned the intended
first hits. No dependency installation is needed. The tool README describes the
source boundary and current search/freshness limitations.

## Mark 01 — The Evidence Finder

Pepe searches scattered ochre stones with a charcoal magnifying lens: a worker
finding a useful passage among unfamiliar material. The first mark occupies the
left central part of the wall, leaving broad areas of bare rock for successors.

Image outputs:

- `artifacts/line-3/wall.png`: PNG, RGB, 1254 × 1254 pixels, square, preserving
  the supplied cave's dimensions, major cracks, crystals, warm light, and framing.
- `dist/line-3/01.jpg`: JPEG, RGB, 512 × 512 pixels, a thumbnail of the finished wall.
- `dist/line-3/01.json`: the numbered record, with the PNG's SHA-256 artifact URL.

Review step: viewed the generated wall at its native size before accepting it,
checking recognizable Pepe eyes/mouth, cave-pigment style, hands, cave landmarks,
and the absence of text, borders, logos, or other forbidden marks. Both hands
were inspected for four fingers and one thumb; the fingers on the lens grip are
partly curled. No unmet visual requirement was identified in this review.
Exact background pixel identity is not claimed for an AI image edit.

The built-in image tool was used in edit mode with the bare cave as its reference.
The exact final prompt is saved in [IMAGE_PROMPT.md](IMAGE_PROMPT.md).
The final prompt was: preserve the 1254-square cave, rock, cracks, crystals, light,
and framing; add a small charcoal/ochre/chalk cave painting of recognizable
heavy-lidded Pepe inspecting three ochre stones through a magnifying lens; show
five digits on each hand; leave most rock bare; include no letters, numbers,
signatures, logos, watermarks, borders, or frames. JPEG conversion only resized
the accepted wall and changed its encoding.
