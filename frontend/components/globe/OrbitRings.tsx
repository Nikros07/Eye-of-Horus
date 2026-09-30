"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// Two thin tilted rings suggesting satellite orbits — decorative, but kept
// subtle (low opacity, well outside the atmosphere shell) so they read as
// tactical-display chrome rather than competing with the planet itself.
interface RingConfig {
  radiusScale: number;
  tilt: [number, number, number];
  color: string;
  spin: number;
  satelliteSpeed: number;
  satellitePhase: number;
}

const RINGS: RingConfig[] = [
  { radiusScale: 1.55, tilt: [0.55, 0, 0.12], color: "#D8B36C", spin: 0.035, satelliteSpeed: 0.5, satellitePhase: 0 },
  { radiusScale: 1.85, tilt: [-0.32, 0, 0.78], color: "#5B8DEF", spin: -0.02, satelliteSpeed: -0.35, satellitePhase: 2.4 },
];

function Ring({ config, baseRadius }: { config: RingConfig; baseRadius: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const satRef = useRef<THREE.Mesh>(null);
  const r = baseRadius * config.radiusScale;

  useFrame((state, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += config.spin * delta;
    if (satRef.current) {
      const t = state.clock.getElapsedTime() * config.satelliteSpeed + config.satellitePhase;
      satRef.current.position.set(Math.cos(t) * r, 0, Math.sin(t) * r);
    }
  });

  return (
    <group ref={groupRef} rotation={config.tilt}>
      <mesh>
        <torusGeometry args={[r, 0.005, 8, 160]} />
        <meshBasicMaterial color={config.color} transparent opacity={0.3} toneMapped={false} />
      </mesh>
      <mesh ref={satRef}>
        <sphereGeometry args={[0.018, 8, 8]} />
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </mesh>
    </group>
  );
}

export default function OrbitRings({ radius = 2.2 }: { radius?: number }) {
  return (
    <>
      {RINGS.map((cfg, i) => (
        <Ring key={i} config={cfg} baseRadius={radius} />
      ))}
    </>
  );
}
