"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard, Html } from "@react-three/drei";
import * as THREE from "three";
import { useRouter } from "next/navigation";
import type { EventSummary } from "@/lib/types";
import { titleCase } from "@/lib/format";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "#F17178",
  high: "#EACB8C",
  medium: "#82AAF5",
  low: "#8B94A3",
};

function latLonToVec3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

// A soft radial-gradient sprite used as an additive glow behind each marker
// — cheap (one shared texture for every marker) and reads as a real point
// light rather than a flat dot.
let glowTexture: THREE.Texture | null = null;
function getGlowTexture(): THREE.Texture {
  if (glowTexture) return glowTexture;
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.35, "rgba(255,255,255,0.5)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  glowTexture = new THREE.CanvasTexture(canvas);
  return glowTexture;
}

function Marker({ event, radius }: { event: EventSummary; radius: number }) {
  const router = useRouter();
  const [hovered, setHovered] = useState(false);
  const ringRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Sprite>(null);
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);
  const color = SEVERITY_COLOR[event.severity] || SEVERITY_COLOR.low;
  const isCritical = event.severity === "critical";

  const position = useMemo(() => latLonToVec3(event.lat, event.lon, radius + 0.015), [event.lat, event.lon, radius]);

  useFrame(({ clock }) => {
    const t = (clock.getElapsedTime() * 0.6 + phase) % 1;
    if (ringRef.current) {
      ringRef.current.scale.setScalar(0.5 + t * 2.6);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.6 * (1 - t);
    }
    if (glowRef.current) {
      const pulse = 1 + Math.sin(clock.getElapsedTime() * 1.6 + phase) * 0.12;
      glowRef.current.scale.setScalar((isCritical ? 0.32 : 0.24) * pulse);
    }
  });

  return (
    <group position={position}>
      <sprite ref={glowRef} scale={isCritical ? 0.32 : 0.24}>
        <spriteMaterial
          map={getGlowTexture()}
          color={color}
          transparent
          opacity={0.9}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </sprite>

      <mesh
        onClick={(e) => {
          e.stopPropagation();
          router.push(`/events/${event.event_id}`);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[isCritical ? 0.05 : 0.036, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>

      <Billboard>
        <mesh ref={ringRef}>
          <ringGeometry args={[0.05, 0.064, 32]} />
          <meshBasicMaterial color={color} transparent opacity={0.55} toneMapped={false} side={THREE.DoubleSide} />
        </mesh>
      </Billboard>

      {hovered && (
        <Html distanceFactor={8} position={[0, 0.14, 0]} style={{ pointerEvents: "none" }}>
          <div className="w-52 -translate-x-1/2 rounded-lg border border-white/10 bg-ink-900/95 p-3 text-left shadow-2xl backdrop-blur">
            <div className="text-[9px] font-semibold uppercase tracking-wider text-text-tertiary">
              {titleCase(event.event_type)}
            </div>
            <div className="mt-1 text-[12px] font-semibold leading-snug text-text-primary">{event.title}</div>
            <div className="mt-1.5 flex items-center gap-2 text-[10px]">
              <span style={{ color }} className="font-bold uppercase">
                {event.severity}
              </span>
              <span className="text-text-tertiary">{Math.round(event.confidence * 100)}% confidence</span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

export default function EventMarkers({ events, radius = 2.2 }: { events: EventSummary[]; radius?: number }) {
  return (
    <>
      {events.map((event) => (
        <Marker key={event.event_id} event={event} radius={radius} />
      ))}
    </>
  );
}
