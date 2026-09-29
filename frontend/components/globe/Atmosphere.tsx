"use client";

import * as THREE from "three";

const vertexShader = `
varying vec3 vNormal;
void main() {
  vNormal = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

// Two shells layered together: a tight, bright rim right at the horizon and
// a softer, wider halo further out — a single shell reads as a flat glowing
// outline, two reads as genuine atmospheric depth.
const fragmentShaderInner = `
varying vec3 vNormal;
void main() {
  float intensity = pow(0.72 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.0);
  gl_FragColor = vec4(0.5, 0.7, 1.0, 1.0) * intensity * 1.35;
}
`;

const fragmentShaderOuter = `
varying vec3 vNormal;
void main() {
  float intensity = pow(0.55 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.2);
  gl_FragColor = vec4(0.4, 0.58, 0.95, 1.0) * intensity * 1.5;
}
`;

export default function Atmosphere({ radius = 2.2 }: { radius?: number }) {
  return (
    <>
      <mesh scale={1.1}>
        <sphereGeometry args={[radius, 64, 64]} />
        <shaderMaterial
          vertexShader={vertexShader}
          fragmentShader={fragmentShaderInner}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
          transparent
        />
      </mesh>
      <mesh scale={1.32}>
        <sphereGeometry args={[radius, 64, 64]} />
        <shaderMaterial
          vertexShader={vertexShader}
          fragmentShader={fragmentShaderOuter}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
          transparent
        />
      </mesh>
    </>
  );
}
