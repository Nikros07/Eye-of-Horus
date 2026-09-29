"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import Earth from "./Earth";
import Atmosphere from "./Atmosphere";
import EventMarkers from "./EventMarkers";
import type { EventSummary } from "@/lib/types";

function EarthFallback({ radius = 2.2 }: { radius?: number }) {
  return (
    <mesh>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial color="#0A0E14" />
    </mesh>
  );
}

export default function GlobalGlobe({ events, className }: { events: EventSummary[]; className?: string }) {
  return (
    <div className={className}>
      <Canvas camera={{ position: [0, 0, 6.2], fov: 42 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[4, 2.2, 4.5]} intensity={1.2} color="#F4E4C1" />
        <directionalLight position={[-5, -2, -5]} intensity={0.2} color="#5B8DEF" />

        <Stars radius={80} depth={40} count={2600} factor={2.2} saturation={0} fade speed={0.4} />

        <Suspense fallback={<EarthFallback radius={2.2} />}>
          <Earth radius={2.2} />
        </Suspense>
        <Atmosphere radius={2.2} />
        <EventMarkers events={events} radius={2.2} />

        <OrbitControls
          enablePan={false}
          enableZoom={true}
          minDistance={3.6}
          maxDistance={9}
          autoRotate
          autoRotateSpeed={0.55}
          rotateSpeed={0.5}
          enableDamping
          dampingFactor={0.08}
        />
      </Canvas>
    </div>
  );
}
