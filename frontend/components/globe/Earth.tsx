"use client";

import { useMemo } from "react";
import { useLoader } from "@react-three/fiber";
import * as THREE from "three";
import { withBasePath } from "@/lib/basePath";

/**
 * Real photographic Earth textures (day / night city-lights / topology),
 * self-hosted from public/textures — copied once from the `three-globe`
 * npm package's bundled example assets (MIT licensed, sourced from NASA
 * Visible Earth / Blue Marble public-domain imagery) rather than fetched
 * from a CDN at runtime, so the globe never depends on outbound network
 * access once the app is built.
 *
 * A custom day/night shader blends the two texture maps across a soft
 * terminator line based on a fixed sun direction — the same technique
 * used by most "living globe" visualizations — instead of a single flat
 * texture, which is what makes the sphere read as a real planet rather
 * than a decal.
 */

const vertexShader = `
varying vec2 vUv;
varying vec3 vNormal;
void main() {
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const fragmentShader = `
uniform sampler2D dayTexture;
uniform sampler2D nightTexture;
uniform sampler2D reliefTexture;
uniform vec3 sunDirection;
varying vec2 vUv;
varying vec3 vNormal;

void main() {
  float sunFactor = dot(vNormal, normalize(sunDirection));
  float blend = smoothstep(-0.18, 0.22, sunFactor);

  vec3 dayColor = texture2D(dayTexture, vUv).rgb;
  vec3 nightColor = texture2D(nightTexture, vUv).rgb * vec3(1.15, 1.05, 0.85) * 1.6;
  vec3 color = mix(nightColor, dayColor, blend);

  float relief = texture2D(reliefTexture, vUv).r;
  color *= (0.9 + relief * 0.12);

  float rim = pow(1.0 - max(dot(vNormal, vec3(0.0, 0.0, 1.0)), 0.0), 2.5);
  color += vec3(0.35, 0.5, 0.85) * rim * 0.15;

  gl_FragColor = vec4(color, 1.0);
}
`;

export default function Earth({ radius = 2.2 }: { radius?: number }) {
  const [dayMap, nightMap, reliefMap] = useLoader(THREE.TextureLoader, [
    withBasePath("/textures/earth-day.jpg"),
    withBasePath("/textures/earth-night.jpg"),
    withBasePath("/textures/earth-topology.png"),
  ]);

  const uniforms = useMemo(
    () => ({
      dayTexture: { value: dayMap },
      nightTexture: { value: nightMap },
      reliefTexture: { value: reliefMap },
      sunDirection: { value: new THREE.Vector3(4, 2.2, 4.5).normalize() },
    }),
    [dayMap, nightMap, reliefMap]
  );

  return (
    <mesh>
      <sphereGeometry args={[radius, 128, 128]} />
      <shaderMaterial vertexShader={vertexShader} fragmentShader={fragmentShader} uniforms={uniforms} />
    </mesh>
  );
}
