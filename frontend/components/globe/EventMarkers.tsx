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

function Marker({ event, radius }: { event: EventSummary; radius: number }) {
  const router = useRouter();
  const [hovered, setHovered] = useState(false);
  const ringRef = useRef<THREE.Mesh>(null);
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);
  const color = SEVERITY_COLOR[event.severity] || SEVERITY_COLOR.low;

  const position = useMemo(() => latLonToVec3(event.lat, event.lon, radius + 0.015), [event.lat, event.lon, radius]);
  const normal = useMemo(() => position.clone().normalize(), [position]);

  useFrame(({ clock }) => {
    if (!ringRef.current) return;
    const t = (clock.getElapsedTime() * 0.6 + phase) % 1;
    ringRef.current.scale.setScalar(0.5 + t * 2.2);
    (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.55 * (1 - t);
  });

  return (
    <group position={position}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          router.push(`/events/${event.event_id}`);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
        }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[event.severity === "critical" ? 0.045 : 0.032, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>

      <Billboard>
        <mesh ref={ringRef}>
          <ringGeometry args={[0.05, 0.062, 32]} />
          <meshBasicMaterial color={color} transparent opacity={0.5} toneMapped={false} side={THREE.DoubleSide} />
        </mesh>
      </Billboard>

      {hovered && (
        <Html distanceFactor={8} position={[0, 0.1, 0]} style={{ pointerEvents: "none" }}>
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
