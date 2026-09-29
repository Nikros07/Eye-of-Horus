"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Decorative shipping-lane layer, same demo/live split as FlightMarkers —
 * a real deployment would poll AISStream.io (free, key required) behind
 * this interface. Vessels crawl much slower than aircraft and sit right on
 * the surface rather than at altitude.
 */
const ROUTES: [string, [number, number], string, [number, number]][] = [
  ["Rotterdam", [51.9, 4.48], "New York", [40.7, -74.0]],
  ["Singapore", [1.29, 103.85], "Shanghai", [31.23, 121.47]],
  ["Suez", [27.0, 34.0], "Mumbai", [19.08, 72.88]],
  ["Los Angeles", [33.7, -118.2], "Shanghai", [31.23, 121.47]],
  ["Santos", [-23.96, -46.33], "Rotterdam", [51.9, 4.48]],
];

function latLonToVec3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

function Vessel({
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
  const surface = radius + 0.008;

  const a = useMemo(() => latLonToVec3(from[0], from[1], surface), [from, surface]);
  const b = useMemo(() => latLonToVec3(to[0], to[1], surface), [to, surface]);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const raw = (clock.getElapsedTime() * speed + phase) % 2;
    const t = 1 - Math.abs(raw - 1);
    const pos = new THREE.Vector3().lerpVectors(a, b, t).normalize().multiplyScalar(surface);
    meshRef.current.position.copy(pos);
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.02, 6, 6]} />
      <meshBasicMaterial color="#EACB8C" toneMapped={false} transparent opacity={0.85} />
    </mesh>
  );
}

export default function VesselMarkers({ radius = 2.2 }: { radius?: number }) {
  return (
    <>
      {ROUTES.map(([, from, , to], i) => (
        <Vessel key={i} from={from} to={to} radius={radius} speed={0.006 + (i % 2) * 0.003} phase={i * 1.3} />
      ))}
    </>
  );
}
