/**
 * VoiceOrb3D — An audio-reactive 3D sphere using React Three Fiber.
 *
 * The sphere geometry is distorted in real-time by frequency data,
 * creating a pulsating, organic "voice orb" effect.
 */

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

// ── Inner animated sphere ──
function AnimatedSphere({ frequencyData, isActive }) {
  const meshRef = useRef();
  const materialRef = useRef();

  // Compute average amplitude from frequency data
  const getAmplitude = () => {
    if (!frequencyData || frequencyData.length === 0) return 0;
    let sum = 0;
    const len = Math.min(frequencyData.length, 64); // focus on lower frequencies
    for (let i = 0; i < len; i++) sum += frequencyData[i];
    return sum / len;
  };

  useFrame((state, delta) => {
    if (!meshRef.current) return;

    const amplitude = getAmplitude();
    const time = state.clock.getElapsedTime();

    // Organic rotation
    meshRef.current.rotation.x = Math.sin(time * 0.3) * 0.2;
    meshRef.current.rotation.y += delta * 0.15;

    // Scale based on audio amplitude
    const baseScale = isActive ? 1.1 : 1.0;
    const audioScale = 1 + amplitude * 0.6;
    const targetScale = baseScale * audioScale;
    meshRef.current.scale.lerp(
      new THREE.Vector3(targetScale, targetScale, targetScale),
      0.1
    );

    // Distort factor follows amplitude
    if (materialRef.current) {
      const targetDistort = isActive ? 0.3 + amplitude * 0.5 : 0.15;
      materialRef.current.distort = THREE.MathUtils.lerp(
        materialRef.current.distort,
        targetDistort,
        0.08
      );
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1.4, 20]} />
      <MeshDistortMaterial
        ref={materialRef}
        color="#ff007f"
        emissive="#ff0033"
        emissiveIntensity={0.6}
        roughness={0.2}
        metalness={0.8}
        distort={0.15}
        speed={2}
        transparent
        opacity={0.92}
      />
    </mesh>
  );
}

// ── Ambient glow ring ──
function GlowRing({ isActive }) {
  const ringRef = useRef();

  useFrame((state) => {
    if (!ringRef.current) return;
    const time = state.clock.getElapsedTime();
    ringRef.current.rotation.z = time * 0.1;
    const pulse = isActive ? 1.05 + Math.sin(time * 3) * 0.05 : 1.0;
    ringRef.current.scale.set(pulse, pulse, 1);
  });

  return (
    <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[2.0, 0.015, 16, 100]} />
      <meshBasicMaterial
        color={isActive ? '#ff3399' : '#ff0033'}
        transparent
        opacity={isActive ? 0.8 : 0.4}
      />
    </mesh>
  );
}

// ── Floating particles ──
function Particles({ count = 80 }) {
  const pointsRef = useRef();

  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const radius = 2.5 + Math.random() * 1.5;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = radius * Math.cos(phi);
    }
    return pos;
  }, [count]);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial size={0.02} color="#ff3399" transparent opacity={0.7} />
    </points>
  );
}

// ── Main exported component ──
export default function VoiceOrb3D({ frequencyData, isActive }) {
  return (
    <div className="w-full h-full" id="voice-orb-canvas">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} color="#ff99cc" />
        <pointLight position={[-3, -3, -3]} intensity={0.5} color="#ff007f" />

        <AnimatedSphere frequencyData={frequencyData} isActive={isActive} />
        <GlowRing isActive={isActive} />
        <Particles />

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          autoRotate
          autoRotateSpeed={0.5}
          maxPolarAngle={Math.PI / 1.5}
          minPolarAngle={Math.PI / 3}
        />
      </Canvas>
    </div>
  );
}
