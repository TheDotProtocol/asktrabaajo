"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";

const R = 1.62;

const HUBS = [
  { name: "London", lat: 51.5, lon: -0.12 },
  { name: "New York", lat: 40.7, lon: -74 },
  { name: "Tokyo", lat: 35.7, lon: 139.7 },
  { name: "Nairobi", lat: -1.29, lon: 36.8 },
  { name: "Singapore", lat: 1.35, lon: 103.8 },
  { name: "São Paulo", lat: -23.5, lon: -46.6 },
  { name: "Berlin", lat: 52.5, lon: 13.4 },
  { name: "Mumbai", lat: 19.1, lon: 72.9 },
  { name: "Sydney", lat: -33.9, lon: 151.2 },
  { name: "Toronto", lat: 43.7, lon: -79.4 },
  { name: "Dubai", lat: 25.2, lon: 55.3 },
  { name: "Lagos", lat: 6.5, lon: 3.4 },
];

const ARCS = [
  [0, 1], [0, 6], [0, 9], [1, 5], [1, 8], [2, 4], [2, 9],
  [3, 0], [3, 10], [4, 8], [4, 7], [6, 11], [7, 10], [5, 3], [10, 2],
];

const latLonToVec = (lat, lon, radius = R) => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
};

const GlobePoints = () => {
  const { positions, count } = useMemo(() => {
    const N = 1600;
    const arr = new Float32Array(N * 3);
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const rad = Math.sqrt(1 - y * y);
      const theta = golden * i;
      arr[i * 3] = Math.cos(theta) * rad * R;
      arr[i * 3 + 1] = y * R;
      arr[i * 3 + 2] = Math.sin(theta) * rad * R;
    }
    return { positions: arr, count: N };
  }, []);

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.021} color="#8b94a5" transparent opacity={0.9} sizeAttenuation depthWrite={false} />
    </points>
  );
};

const Hub = ({ position }) => (
  <group position={position}>
    <mesh>
      <sphereGeometry args={[0.022, 12, 12]} />
      <meshBasicMaterial color="#E7C968" />
    </mesh>
    <mesh>
      <sphereGeometry args={[0.05, 12, 12]} />
      <meshBasicMaterial color="#D4AF37" transparent opacity={0.22} depthWrite={false} />
    </mesh>
  </group>
);

const Arc = ({ from, to, speed }) => {
  const ref = useRef();
  const points = useMemo(() => {
    const a = latLonToVec(from.lat, from.lon);
    const b = latLonToVec(to.lat, to.lon);
    const mid = a.clone().add(b).multiplyScalar(0.5);
    const lift = 1 + a.distanceTo(b) * 0.28;
    mid.normalize().multiplyScalar(R * lift);
    const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
    return curve.getPoints(48);
  }, [from, to]);

  useFrame((_, delta) => {
    if (ref.current) ref.current.material.dashOffset -= delta * speed;
  });

  return (
    <Line
      ref={ref}
      points={points}
      color="#D4AF37"
      transparent
      opacity={0.5}
      lineWidth={1}
      dashed
      dashSize={0.12}
      gapSize={0.22}
    />
  );
};

const Atmosphere = () => (
  <mesh>
    <sphereGeometry args={[R * 1.16, 48, 48]} />
    <meshBasicMaterial color="#D4AF37" transparent opacity={0.035} side={THREE.BackSide} depthWrite={false} />
  </mesh>
);

const Scene = () => {
  const group = useRef();

  useFrame((state, delta) => {
    if (!group.current) return;
    group.current.rotation.y += delta * 0.06;
    const px = state.pointer.x;
    const py = state.pointer.y;
    group.current.rotation.x += (py * 0.12 - group.current.rotation.x) * 0.03;
    group.current.rotation.z += (px * 0.05 - group.current.rotation.z) * 0.03;
  });

  return (
    <group ref={group} rotation={[0.28, 0, 0]} position={[0.55, -0.1, 0]}>
      <GlobePoints />
      <Atmosphere />
      {HUBS.map((h) => (
        <Hub key={h.name} position={latLonToVec(h.lat, h.lon)} />
      ))}
      {ARCS.map(([a, b], i) => (
        <Arc key={i} from={HUBS[a]} to={HUBS[b]} speed={0.15 + (i % 4) * 0.06} />
      ))}
    </group>
  );
};

export const GlobeScene = () => (
  <Canvas
    data-testid="hero-globe-canvas"
    camera={{ position: [0, 0.15, 4.4], fov: 42 }}
    dpr={[1, 1.8]}
    gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
    style={{ background: "transparent" }}
    aria-hidden="true"
  >
    <Scene />
  </Canvas>
);

export default GlobeScene;
