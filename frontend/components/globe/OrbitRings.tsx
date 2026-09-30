"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Trail } from "@react-three/drei";
import * as THREE from "three";

/**
 * Two small satellites orbiting the globe, each dragging a short glowing
 * trail behind it — suggests satellite-tracking chrome without a static
 * ring. An earlier version drew a full torus for each orbit, but a thin
 * ring on a fixed tilt combined with the camera's horizontal-only
 * auto-rotate orbit (constant elevation) means the viewing angle relative
 * to the ring's plane never swings through a genuinely face-on range —
 * it foreshortens toward a line for most of every rotation, reading as a
 * stray streak across open space rather than a ring around the planet.
 * A moving point's trail has no such failure mode: it's always a short,
 * bounded arc trailing a dot, never a persistent full-circle line, so it
 * can't foreshorten into anything that reads as broken.
 */
interface OrbitConfig {
  radiusScale: number;
  tilt: [number, number, number];
  color: string;
  speed: number;
  phase: number;
}

const ORBITS: OrbitConfig[] = [
  { radiusScale: 1.4, tilt: [0.55, 0, 0.12], color: "#D8B36C", speed: 0.22, phase: 0 },
  { radiusScale: 1.55, tilt: [-0.32, 0, 0.78], color: "#5B8DEF", speed: -0.16, phase: 2.4 },
];

function Satellite({ config, baseRadius }: { config: OrbitConfig; baseRadius: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const r = baseRadius * config.radiusScale;
  const tiltQuat = useRef(new THREE.Quaternion().setFromEuler(new THREE.Euler(...config.tilt)));
  const pos = useRef(new THREE.Vector3());

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.getElapsedTime() * config.speed + config.phase;
    pos.current.set(Math.cos(t) * r, 0, Math.sin(t) * r).applyQuaternion(tiltQuat.current);
    meshRef.current.position.copy(pos.current);
  });

  return (
    <Trail width={1.3} length={6} color={config.color} attenuation={(w) => w} decay={1}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </mesh>
    </Trail>
  );
}

export default function OrbitRings({ radius = 2.2 }: { radius?: number }) {
  return (
    <>
      {ORBITS.map((cfg, i) => (
        <Satellite key={i} config={cfg} baseRadius={radius} />
      ))}
    </>
  );
}
