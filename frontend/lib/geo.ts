import * as THREE from "three";

// Standard lat/lon -> sphere-surface conversion shared by every globe layer
// (event markers, flight/vessel trails) so they all place points on exactly
// the same sphere with the same orientation.
export function latLonToVec3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}
