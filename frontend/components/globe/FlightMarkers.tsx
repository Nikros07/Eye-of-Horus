"use client";

import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { MeshLineGeometry, MeshLineMaterial } from "meshline";
import * as THREE from "three";
import { latLonToVec3 } from "@/lib/geo";

/**
 * Decorative live-traffic layer. Routes are real major city pairs; motion is
 * a cheap lerp-then-normalize great-circle approximation (fine at this
 * visual scale) ping-ponging back and forth so nothing ever visibly teleports.
 * This is a stand-in for a real OpenSky Network feed — OpenSky's anonymous
 * REST API is free and keyless, but unreachable from this sandbox's network
 * policy, so `DATA_MODE=live` would wire a real poller in here behind the
 * same interface, exactly like the event/market connectors.
 *
 * The trail used to be drei's <Trail>, which (see OrbitRings.tsx for the
 * full diagnosis) accumulates one point per *rendered frame* rather than
 * per unit of real time or distance — so its on-screen length scales with
 * frame rate, not flight speed. That turned out to affect this component
 * too: a diagnostic sweep with OrbitRings disabled still showed a long
 * diagonal streak, proving it, not the orbit rings, was the second source
 * of the "line across the globe" bug. Fixed the same way: each frame
 * recomputes a short trailing arc directly from this component's own
 * position formula (lerp + normalize) evaluated at a handful of slightly
 * earlier real timestamps, rendered via MeshLine (the library drei's Trail
 * wraps) instead of accumulated frame history.
 */
const TRAIL_SECONDS = 0.4;
const TRAIL_SEGMENTS = 10;
const TRAIL_LINE_WIDTH = 0.05;

const ROUTES: [string, [number, number], string, [number, number]][] = [
  ["JFK", [40.64, -73.78], "LHR", [51.47, -0.45]],
  ["LAX", [33.94, -118.41], "NRT", [35.76, 140.39]],
  ["DXB", [25.25, 55.36], "SIN", [1.35, 103.99]],
  ["FRA", [50.03, 8.57], "JFK", [40.64, -73.78]],
  ["SYD", [-33.95, 151.18], "LAX", [33.94, -118.41]],
  ["GRU", [-23.43, -46.47], "MAD", [40.47, -3.56]],
  ["HKG", [22.31, 113.91], "SFO", [37.62, -122.38]],
  ["CDG", [49.01, 2.55], "JNB", [-26.13, 28.24]],
];

function flightPosition(
  a: THREE.Vector3,
  b: THREE.Vector3,
  altitude: number,
  elapsed: number,
  speed: number,
  phase: number,
  out: THREE.Vector3
) {
  const raw = (elapsed * speed + phase) % 2;
  const t = 1 - Math.abs(raw - 1); // ping-pong 0 -> 1 -> 0, no jump
  out.lerpVectors(a, b, t).normalize().multiplyScalar(altitude);
  return raw;
}

function Flight({
  from,
  to,
  radius,
  speed,
  phase,
}: {
  from: [number, number];
  to: [number, number];
  radius: number;
  speed: number;
  phase: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const altitude = radius + 0.05;

  const a = useMemo(() => latLonToVec3(from[0], from[1], altitude), [from, altitude]);
  const b = useMemo(() => latLonToVec3(to[0], to[1], altitude), [to, altitude]);
  const size = useThree((s) => s.size);

  const geo = useMemo(() => new MeshLineGeometry(), []);
  const mat = useMemo(() => {
    const m = new MeshLineMaterial({
      lineWidth: TRAIL_LINE_WIDTH,
      color: new THREE.Color("#82AAF5"),
      sizeAttenuation: 1,
      opacity: 0.85,
      resolution: new THREE.Vector2(size.width, size.height),
    });
    m.transparent = true;
    m.toneMapped = false;
    return m;
  }, [size.width, size.height]);

  const trailPoints = useRef(new Float32Array((TRAIL_SEGMENTS + 1) * 3));
  const sample = useRef(new THREE.Vector3());

  useFrame(({ clock }) => {
    const now = clock.getElapsedTime();
    // Speed is always positive here, so `raw` increases monotonically and
    // each leg (one full ping-pong direction) spans exactly one integer
    // step of `raw` — this is how far back into the current leg we can
    // look without crossing a reversal, where the ribbon's miter geometry
    // degenerates (see the header comment).
    const rawNow = (now * speed + phase) % 2;
    const legStartRaw = Math.floor(rawNow);
    const timeSinceLegStart = (rawNow - legStartRaw) / speed;
    const effectiveTrailSeconds = Math.min(TRAIL_SECONDS, timeSinceLegStart);

    const arr = trailPoints.current;
    for (let i = 0; i <= TRAIL_SEGMENTS; i++) {
      const timeOffset = (1 - i / TRAIL_SEGMENTS) * effectiveTrailSeconds;
      flightPosition(a, b, altitude, now - timeOffset, speed, phase, sample.current);
      arr[i * 3] = sample.current.x;
      arr[i * 3 + 1] = sample.current.y;
      arr[i * 3 + 2] = sample.current.z;
    }
    geo.setPoints(arr, (w) => w);

    if (meshRef.current) {
      meshRef.current.position.set(
        arr[TRAIL_SEGMENTS * 3],
        arr[TRAIL_SEGMENTS * 3 + 1],
        arr[TRAIL_SEGMENTS * 3 + 2]
      );
    }
  });

  return (
    <>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.014, 6, 6]} />
        <meshBasicMaterial color="#CFE0FF" toneMapped={false} />
      </mesh>
      <mesh geometry={geo} material={mat} />
    </>
  );
}

export default function FlightMarkers({ radius = 2.2 }: { radius?: number }) {
  return (
    <>
      {ROUTES.map(([, from, , to], i) => (
        <Flight key={i} from={from} to={to} radius={radius} speed={0.05 + (i % 3) * 0.012} phase={i * 0.7} />
      ))}
    </>
  );
}
