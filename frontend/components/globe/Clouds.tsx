"use client";

import { useLoader, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { withBasePath } from "@/lib/basePath";

// A thin translucent shell just above the surface, drifting independently
// of both the planet and the camera — real cloud cover doesn't track the
// viewer, so a fixed self-rotation (rather than tying it to auto-rotate)
// is what actually reads as weather moving over a static globe.
const DRIFT_RADIANS_PER_SECOND = 0.0045;

export default function Clouds({ radius = 2.2 }: { radius?: number }) {
  const mesh = useRef<THREE.Mesh>(null);
  const cloudMap = useLoader(THREE.TextureLoader, withBasePath("/textures/earth-clouds.png"));

  useFrame((_, delta) => {
    if (mesh.current) mesh.current.rotation.y += DRIFT_RADIANS_PER_SECOND * delta;
  });

  return (
    <mesh ref={mesh} scale={1.015}>
      <sphereGeometry args={[radius, 96, 96]} />
      <meshStandardMaterial map={cloudMap} transparent opacity={0.55} depthWrite={false} roughness={1} />
    </mesh>
  );
}
