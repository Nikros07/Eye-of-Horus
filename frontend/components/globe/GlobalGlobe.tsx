"use client";

import { Suspense, useCallback, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import clsx from "clsx";
import Earth from "./Earth";
import Clouds from "./Clouds";
import Atmosphere from "./Atmosphere";
import OrbitRings from "./OrbitRings";
import EventMarkers from "./EventMarkers";
import FlightMarkers from "./FlightMarkers";
import VesselMarkers from "./VesselMarkers";
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

export default function GlobalGlobe({
  events,
  className,
  showTraffic = true,
}: {
  events: EventSummary[];
  className?: string;
  showTraffic?: boolean;
}) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // Directly nudges the OrbitControls camera distance. Refs cross the R3F
  // Canvas boundary fine — no need to route this through React context, and
  // the canvas already renders every frame (auto-rotate, marker pulses,
  // flight trails), so the change shows up without any manual invalidation.
  const zoom = useCallback((factor: number) => {
    const controls = controlsRef.current;
    if (!controls) return;
    const camera = controls.object as THREE.PerspectiveCamera;
    const dir = new THREE.Vector3().subVectors(camera.position, controls.target);
    const min = controls.minDistance ?? 1;
    const max = controls.maxDistance ?? 100;
    dir.setLength(THREE.MathUtils.clamp(dir.length() * factor, min, max));
    camera.position.copy(controls.target).add(dir);
    controls.update();
  }, []);

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
    <div
      className={clsx(
        expanded ? "fixed inset-3 z-[70] md:inset-8" : `relative ${className || ""}`,
        "transition-all duration-300"
      )}
    >
      {expanded && <div className="absolute inset-0 -z-10 rounded-3xl bg-ink-950/95 backdrop-blur-xl" />}

      <Canvas camera={{ position: [0, 0, 5.2], fov: 42 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[4, 2.2, 4.5]} intensity={1.2} color="#F4E4C1" />
        <directionalLight position={[-5, -2, -5]} intensity={0.2} color="#5B8DEF" />

        <Stars radius={90} depth={45} count={3400} factor={2.4} saturation={0} fade speed={0.35} />

        <Suspense fallback={<EarthFallback radius={2.2} />}>
          <Earth radius={2.2} />
          <Clouds radius={2.2} />
        </Suspense>
        <Atmosphere radius={2.2} />
        <OrbitRings radius={2.2} />
        <EventMarkers events={events} radius={2.2} />
        {showTraffic && (
          <>
            <FlightMarkers radius={2.2} />
            <VesselMarkers radius={2.2} />
          </>
        )}

        <OrbitControls
          ref={controlsRef}
          enablePan={false}
          enableZoom
          minDistance={2.6}
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

        <EffectComposer multisampling={0}>
          <Bloom mipmapBlur luminanceThreshold={0.97} luminanceSmoothing={0.1} intensity={0.3} radius={0.15} />
          <Vignette eskil={false} offset={0.15} darkness={0.55} />
        </EffectComposer>
      </Canvas>

      {/* HUD corner-bracket frame — tactical-display framing for the centerpiece */}
      <div aria-hidden className="pointer-events-none absolute inset-3 md:inset-4">
        <div className="absolute left-0 top-0 h-4 w-4 border-l border-t border-gold/25" />
        <div className="absolute right-0 top-0 h-4 w-4 border-r border-t border-gold/25" />
        <div className="absolute bottom-0 left-0 h-4 w-4 border-b border-l border-gold/25" />
        <div className="absolute bottom-0 right-0 h-4 w-4 border-b border-r border-gold/25" />
      </div>

      <div className="pointer-events-none absolute left-4 top-4 flex items-center gap-1.5">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold-bright opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-gold-bright" />
        </span>
        <span className="font-mono text-[9px] font-semibold uppercase tracking-[0.2em] text-text-tertiary">
          Global Sitrep
        </span>
      </div>

      <div className="pointer-events-none absolute bottom-4 left-4 font-mono text-[9px] uppercase tracking-[0.15em] text-text-faint">
        {events.length} events tracked
      </div>

      {/* Controls overlay */}
      <div className="pointer-events-none absolute right-4 top-4 flex flex-col gap-1.5">
        <button
          type="button"
          onClick={() => zoom(0.78)}
          className="pointer-events-auto flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-ink-950/70 text-text-secondary backdrop-blur transition-colors hover:border-white/20 hover:text-text-primary"
          aria-label="Zoom in"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        <button
          type="button"
          onClick={() => zoom(1.28)}
          className="pointer-events-auto flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-ink-950/70 text-text-secondary backdrop-blur transition-colors hover:border-white/20 hover:text-text-primary"
          aria-label="Zoom out"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="pointer-events-auto flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-ink-950/70 text-text-secondary backdrop-blur transition-colors hover:border-white/20 hover:text-text-primary"
          aria-label={expanded ? "Collapse globe" : "Expand globe"}
        >
          {expanded ? (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M9 5H5V9M9 9L2 2M5 5L12 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M1 5V1H5M9 1H13V5M13 9V13H9M5 13H1V9"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>

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
