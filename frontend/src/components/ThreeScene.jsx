import React, { useRef, useMemo, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import { useTheme } from '../context/ThemeContext';

// ── Drifting particle sphere ─────────────────────────────────────────────────
function Particles({ dark }) {
  const ref = useRef();
  const count = 1400;

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // Distribute over a sphere shell
      const r = 4 + Math.random() * 9;
      const theta = Math.random() * 2 * Math.PI;
      const phi   = Math.acos(2 * Math.random() - 1);
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      arr[i * 3 + 2] = r * Math.cos(phi);
    }
    return arr;
  }, []);

  useFrame((_, delta) => {
    ref.current.rotation.x -= delta * 0.018;
    ref.current.rotation.y -= delta * 0.012;
  });

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        color={dark ? '#818cf8' : '#6366f1'}
        size={0.055}
        sizeAttenuation
        depthWrite={false}
        opacity={dark ? 0.55 : 0.22}
      />
    </Points>
  );
}

// ── Slow-floating wireframe shape ────────────────────────────────────────────
function Shape({ pos, speed, dark }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    ref.current.rotation.x = t * speed * 0.5;
    ref.current.rotation.y = t * speed;
    ref.current.position.y = pos[1] + Math.sin(t * 0.4 + pos[0]) * 0.5;
  });
  return (
    <mesh ref={ref} position={pos}>
      <icosahedronGeometry args={[0.45, 0]} />
      <meshBasicMaterial
        color={dark ? '#818cf8' : '#6366f1'}
        wireframe
        transparent
        opacity={dark ? 0.18 : 0.10}
      />
    </mesh>
  );
}

const SHAPES = [
  { pos: [-5, 2, -4],  speed: 0.18 },
  { pos: [5, -1, -3],  speed: 0.22 },
  { pos: [-3, -3, -5], speed: 0.15 },
  { pos: [4, 3,  -6],  speed: 0.25 },
  { pos: [0, -4, -4],  speed: 0.20 },
  { pos: [-6, 0, -3],  speed: 0.17 },
  { pos: [3, 5,  -5],  speed: 0.28 },
  { pos: [-2, 4, -4],  speed: 0.13 },
];

// ── Exported component ───────────────────────────────────────────────────────
export default function Background3D() {
  const { dark } = useTheme();

  return (
    <div
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    >
      <Canvas
        camera={{ position: [0, 0, 9], fov: 55 }}
        gl={{ alpha: true, antialias: false, powerPreference: 'low-power' }}
        dpr={[1, 1.2]}
      >
        <Suspense fallback={null}>
          <Particles dark={dark} />
          {SHAPES.map((s, i) => <Shape key={i} {...s} dark={dark} />)}
        </Suspense>
      </Canvas>
    </div>
  );
}
