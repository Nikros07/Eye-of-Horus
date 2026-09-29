"use client";

import { Suspense, useCallback, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import Earth from "./Earth";
import Atmosphere from "./Atmosphere";
import EventMarkers from "./EventMarkers";
import type { EventSummary } from "@/lib/types";

const IDLE_RESUME_MS = 2800;

function EarthFallback({ radius = 2.2 }: { radius?: number }) {
  return (
    <mesh>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial color="#0A0E14" />
    </mesh>
  );
}

export default function GlobalGlobe({ events, className }: { events: EventSummary[]; className?: string }) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Full manual control while the user is actively dragging — auto-spin
  // only resumes after a couple of seconds of no input, so it never fights
  // the position you just dragged to.
  const handleStart = useCallback(() => {
    setHasInteracted(true);
    setAutoRotate(false);
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
  }, []);

  const handleEnd = useCallback(() => {
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => setAutoRotate(true), IDLE_RESUME_MS);
  }, []);

  return (
    <div className={`relative ${className || ""}`}>
      <Canvas camera={{ position: [0, 0, 6.2], fov: 42 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[4, 2.2, 4.5]} intensity={1.2} color="#F4E4C1" />
        <directionalLight position={[-5, -2, -5]} intensity={0.2} color="#5B8DEF" />

        <Stars radius={90} depth={45} count={3400} factor={2.4} saturation={0} fade speed={0.35} />

        <Suspense fallback={<EarthFallback radius={2.2} />}>
          <Earth radius={2.2} />
        </Suspense>
        <Atmosphere radius={2.2} />
        <EventMarkers events={events} radius={2.2} />

        <OrbitControls
          ref={controlsRef}
          enablePan={false}
          enableZoom
          minDistance={3.2}
          maxDistance={10}
          minPolarAngle={0}
          maxPolarAngle={Math.PI}
          autoRotate={autoRotate}
          autoRotateSpeed={0.5}
          rotateSpeed={0.85}
          zoomSpeed={0.7}
          enableDamping
          dampingFactor={0.05}
          onStart={handleStart}
          onEnd={handleEnd}
        />
      </Canvas>

      <div
        aria-hidden
        className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-white/10 bg-ink-950/70 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-text-tertiary backdrop-blur transition-opacity duration-700"
        style={{ opacity: hasInteracted ? 0 : 1 }}
      >
        Drag to rotate · Scroll to zoom
      </div>
    </div>
  );
}
