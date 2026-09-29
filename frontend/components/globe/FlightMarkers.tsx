"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Trail } from "@react-three/drei";
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
 */
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
  // Reused across frames instead of allocating a new Vector3 every tick —
  // there are 8 of these animating in lockstep, every frame.
  const pos = useRef(new THREE.Vector3());

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const raw = (clock.getElapsedTime() * speed + phase) % 2;
    const t = 1 - Math.abs(raw - 1); // ping-pong 0 -> 1 -> 0, no jump
    pos.current.lerpVectors(a, b, t).normalize().multiplyScalar(altitude);
    meshRef.current.position.copy(pos.current);
  });

  return (
    <Trail width={1.1} length={4.5} color="#82AAF5" attenuation={(w) => w} decay={1}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.014, 6, 6]} />
        <meshBasicMaterial color="#CFE0FF" toneMapped={false} />
      </mesh>
    </Trail>
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
