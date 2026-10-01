# Texture provenance

`earth-clouds.png` and `earth-topology.png` are copied from the
[`three-globe`](https://github.com/vasturiano/three-globe) npm package's /
[`three.js`](https://github.com/mrdoob/three.js) project's bundled example
assets (MIT licensed), themselves derived from NASA Visible Earth / Blue
Marble public-domain imagery.

`earth-day.jpg`, `earth-night.jpg`, and `earth-specular.jpg` are downsampled
from the [Solar System Scope](https://www.solarsystemscope.com/textures/)
8K Earth texture set (`8k_earth_daymap.jpg`, `8k_earth_nightmap.jpg`,
`8k_earth_specular_map.jpg`), licensed CC BY 4.0 — attribution:
"Solar System Scope / solarsystemscope.com". Chosen over the previous
three.js example textures for noticeably sharper coastlines and city lights
when the globe is zoomed in close, while staying small enough (both resized
down from the original 8192×4096 to 4096×2048 for day/night and 2048×1024
for specular) to keep GPU texture memory and page weight reasonable — the
genuine 8K originals would be ~4x the pixel count per map, which isn't a
worthwhile trade for a background decorative globe.

All five are checked into this repo (rather than fetched from a CDN at
runtime) so the globe has no external network dependency once the app is
built. See `components/globe/Earth.tsx` and `components/globe/Clouds.tsx`
for how they're used.
