"use client";

import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { MeshLineGeometry, MeshLineMaterial } from "meshline";
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
 *
 * Two earlier attempts used drei's <Trail>, tuning its `length` prop on
 * the assumption it was an angular/world-space span. It isn't: per
 * @react-three/drei's Trail.js, `length` only sizes a fixed point-count
 * ring buffer, refilled one point per *rendered frame*. Its on-screen
 * length is therefore however far the satellite moves across however
 * many frames it takes to fill that buffer — i.e. it scales with actual
 * render frame rate, not orbit geometry. A slow/software-rendered
 * frame rate fills the same point count over more wall-clock time,
 * producing a visibly longer trail. A follow-up attempt tried Trail's
 * `stride` prop to bound point spacing by world distance instead, but
 * Trail only compares each frame's position to the *previous frame's*
 * position (not the last point actually recorded) — so stride is a
 * no-op whenever per-frame movement already exceeds it, which made the
 * trail longer, not shorter, once the point count changed too.
 *
 * The only way to make the trail's length independent of frame rate is
 * to stop deriving it from accumulated rendered frames at all. Below,
 * each frame recomputes a short trailing arc directly from the orbit's
 * own closed-form circle equation (the same one driving the satellite's
 * position), sampled at TRAIL_SEGMENTS points spanning exactly
 * TRAIL_ARC_RADIANS of real orbital angle — a MeshLine (the same library
 * drei's Trail uses internally) renders it with a width taper from tail
 * to head. This guarantees the same short, fixed angular span on any
 * device or frame rate, since it's evaluated analytically rather than
 * sampled from history.
 */
const TRAIL_ARC_RADIANS = THREE.MathUtils.degToRad(6);
const TRAIL_SEGMENTS = 14;
const TRAIL_LINE_WIDTH = 0.045;

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
  const tiltQuat = useMemo(
    () => new THREE.Quaternion().setFromEuler(new THREE.Euler(...config.tilt)),
    [config.tilt]
  );
  // Real-time (not frame-count) window whose sweep covers exactly
  // TRAIL_ARC_RADIANS of orbital angle, however fast |speed| carries the
  // satellite around — this is what stays constant across frame rates.
  const tailSeconds = TRAIL_ARC_RADIANS / Math.abs(config.speed);
  const size = useThree((s) => s.size);

  const geo = useMemo(() => new MeshLineGeometry(), []);
  const mat = useMemo(() => {
    const m = new MeshLineMaterial({
      lineWidth: TRAIL_LINE_WIDTH,
      color: new THREE.Color(config.color),
      sizeAttenuation: 1,
      opacity: 0.85,
      resolution: new THREE.Vector2(size.width, size.height),
    });
    m.transparent = true;
    m.toneMapped = false;
    return m;
  }, [config.color, size.width, size.height]);

  const trailPoints = useRef(new Float32Array((TRAIL_SEGMENTS + 1) * 3));
  const sample = useRef(new THREE.Vector3());

  useFrame(({ clock }) => {
    const now = clock.getElapsedTime();
    const arr = trailPoints.current;
    for (let i = 0; i <= TRAIL_SEGMENTS; i++) {
      // i=0 is the oldest/tail sample, i=TRAIL_SEGMENTS is "now"/the head.
      const timeOffset = (1 - i / TRAIL_SEGMENTS) * tailSeconds;
      const t = (now - timeOffset) * config.speed + config.phase;
      sample.current.set(Math.cos(t) * r, 0, Math.sin(t) * r).applyQuaternion(tiltQuat);
      arr[i * 3] = sample.current.x;
      arr[i * 3 + 1] = sample.current.y;
      arr[i * 3 + 2] = sample.current.z;
    }
    geo.setPoints(arr, (w) => w);

    if (meshRef.current) {
      meshRef.current.position.set(
        arr[TRAIL_SEGMENTS * 3],
        arr[TRAIL_SEGMENTS * 3 + 1],
        arr[TRAIL_SEGMENTS * 3 + 2]
      );
    }
  });

  return (
    <>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color={config.color} toneMapped={false} />
      </mesh>
      <mesh geometry={geo} material={mat} />
    </>
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
