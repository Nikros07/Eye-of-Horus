# Texture provenance

`earth-night.jpg` and `earth-topology.png` are copied from the
[`three-globe`](https://github.com/vasturiano/three-globe) npm package's
bundled example assets (MIT licensed), themselves derived from NASA Visible
Earth / Blue Marble public-domain imagery.

`earth-day.jpg`, `earth-clouds.png`, and `earth-specular.jpg` are copied from
the [`three.js`](https://github.com/mrdoob/three.js) project's own example
assets (`examples/textures/planets/earth_atmos_2048.jpg`,
`earth_clouds_1024.png`, `earth_specular_2048.jpg` — MIT licensed), also
NASA-sourced imagery, chosen for their higher resolution and because the
clouds texture ships with a proper alpha channel for a real translucent
cloud layer.

All five are checked into this repo (rather than fetched from a CDN at
runtime) so the globe has no external network dependency once the app is
built. See `components/globe/Earth.tsx` and `components/globe/Clouds.tsx`
for how they're used.
