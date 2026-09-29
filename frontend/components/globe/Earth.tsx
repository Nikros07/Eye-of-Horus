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

// vNormal/vViewDir are computed in world space (not the camera-space
// `normalMatrix`) so the terminator and specular sit at a fixed point on the
// planet as the OrbitControls camera orbits around it — with a camera-space
// normal, both would incorrectly track the camera's rotation instead of the
// fixed `sunDirection` uniform, keeping a "lit" hemisphere facing the viewer
// at every angle and making the night side unreachable.
const vertexShader = `
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewDir;
void main() {
  vUv = uv;
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vNormal = normalize(mat3(modelMatrix) * normal);
  vViewDir = normalize(cameraPosition - worldPosition.xyz);
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

const fragmentShader = `
uniform sampler2D dayTexture;
uniform sampler2D nightTexture;
uniform sampler2D reliefTexture;
uniform sampler2D specularTexture;
uniform vec3 sunDirection;
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewDir;

void main() {
  vec3 sun = normalize(sunDirection);
  float sunFactor = dot(vNormal, sun);
  float blend = smoothstep(-0.18, 0.22, sunFactor);

  vec3 dayColor = texture2D(dayTexture, vUv).rgb;
  vec3 nightColor = texture2D(nightTexture, vUv).rgb * vec3(1.15, 1.05, 0.85) * 1.6;
  vec3 color = mix(nightColor, dayColor, blend);

  float relief = texture2D(reliefTexture, vUv).r;
  color *= (0.9 + relief * 0.12);

  // Ocean specular sheen: the specular map is bright over water, dark over
  // land, so a Blinn-Phong highlight masked by it reads as sunlight glinting
  // off the sea rather than a uniform plastic sheen across the whole sphere.
  float water = texture2D(specularTexture, vUv).r;
  vec3 halfVec = normalize(sun + vViewDir);
  float specAngle = max(dot(vNormal, halfVec), 0.0);
  float specular = pow(specAngle, 220.0) * water * max(sunFactor, 0.0);
  color += vec3(0.9, 0.95, 1.0) * specular * 0.3;

  float rim = pow(1.0 - max(dot(vNormal, vViewDir), 0.0), 2.5);
  color += vec3(0.35, 0.5, 0.85) * rim * 0.15;

  gl_FragColor = vec4(color, 1.0);
}
`;

export default function Earth({ radius = 2.2 }: { radius?: number }) {
  const [dayMap, nightMap, reliefMap, specularMap] = useLoader(THREE.TextureLoader, [
    withBasePath("/textures/earth-day.jpg"),
    withBasePath("/textures/earth-night.jpg"),
    withBasePath("/textures/earth-topology.png"),
    withBasePath("/textures/earth-specular.jpg"),
  ]);

  const uniforms = useMemo(
    () => ({
      dayTexture: { value: dayMap },
      nightTexture: { value: nightMap },
      reliefTexture: { value: reliefMap },
      specularTexture: { value: specularMap },
      sunDirection: { value: new THREE.Vector3(4, 2.2, 4.5).normalize() },
    }),
    [dayMap, nightMap, reliefMap, specularMap]
  );

  return (
    <mesh>
      <sphereGeometry args={[radius, 128, 128]} />
      <shaderMaterial vertexShader={vertexShader} fragmentShader={fragmentShader} uniforms={uniforms} />
    </mesh>
  );
}
