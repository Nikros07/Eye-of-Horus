# Texture provenance

`earth-day.jpg`, `earth-night.jpg`, `earth-topology.png` are copied from the
[`three-globe`](https://github.com/vasturiano/three-globe) npm package's
bundled example assets (MIT licensed), which are themselves derived from
NASA Visible Earth / Blue Marble public-domain imagery. They are checked
into this repo (rather than fetched from a CDN at runtime) so the globe has
no external network dependency once the app is built. See
`components/globe/Earth.tsx` for how they're used.
