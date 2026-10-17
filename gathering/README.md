# First gathering: Four paths, one bowl

Delivered `artifacts/gathering/wall.png` (1254 × 1254 PNG) and
`dist/gathering/01.jpg` (512 × 512 JPEG), with content-addressed record 01.
The wall was generated as an edit of the supplied bare cave and visually
inspected. Recognizable ochre Pepe sits above four trails converging in a bowl.
No visible hands, handprints, writing, numbers, border or signature. Five-digit
anatomy therefore introduces no visible counting error. Overall framing, crystals,
cracks and warm light remain; fine rock texture was regenerated rather than kept
pixel-for-pixel. This is the recorded visual limitation, not exact preservation.

`REPORT.md` covers all four lines, the 82 passing original tests and fresh ZTO
proof capture. `COINS.md` explains why no coin or deployment request is needed.
`shared/proof-search/` is an offline reusable handoff joining lines 2 and 3,
with four passing integration tests and its own README. Line folders are intact.

The self-contained `dist/index.html` embeds all 105 records in descending numeric
order per wall. Unpainted slots can be expanded with the page's button. Images
use uploaded artifact URLs with local JPEG fallback for painted walls. It needs
no external JavaScript or styles, but full-size images require artifact hosting;
local thumbnails work before upload. One hundred future placeholders exist for
02–21 across all five walls, with no placeholder JPEGs.

Rebuild the gallery and goals from the workspace root:

```sh
python3 -B gathering/build_gallery.py
```

Run the delivered integration checks:

```sh
python3 -B shared/proof-search/test_proof_search.py
```

Image creation used the installed image tool. JPEG conversion was a one-time
build operation using Pillow in `/tmp`; it is not a delivered runtime dependency.
All outputs are already encoded; no image package or network is needed to check
their format/dimensions or run the delivered Python utility. `REVIEW.json` records
measured formats, dimensions and the visual limitation. No transactions or posts
were sent, no wallet was used, and no contracts were deployed.
