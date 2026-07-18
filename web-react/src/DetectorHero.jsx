import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';

function useCappedAnimation(fps = 24) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      invalidate();
      return undefined;
    }
    const timer = window.setInterval(invalidate, 1000 / fps);
    return () => window.clearInterval(timer);
  }, [fps, invalidate]);
}

function DetectorAssembly() {
  const assembly = useRef(null);
  useCappedAnimation();
  useFrame(({ clock }, delta) => {
    if (!assembly.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    assembly.current.rotation.y += Math.min(delta, 0.05) * 0.12;
    assembly.current.rotation.x = -0.28 + Math.sin(clock.elapsedTime * 0.35) * 0.025;
    assembly.current.position.y = Math.sin(clock.elapsedTime * 0.45) * 0.06;
  });

  const pixelLines = Array.from({ length: 9 }, (_, index) => -1.6 + index * 0.4);
  const strikes = [
    { position: [-1.05, 0.28, 0.22], rotation: [0, 0, -0.72], length: 1.35 },
    { position: [0.55, -0.35, 0.24], rotation: [0, 0, 0.48], length: 1.05 },
    { position: [1.2, 0.72, 0.23], rotation: [0, 0, -0.2], length: 0.72 },
  ];

  return (
    <group ref={assembly} rotation={[-0.28, -0.36, 0.04]}>
      <mesh>
        <boxGeometry args={[3.7, 2.45, 0.16]} />
        <meshStandardMaterial color="#071a1d" metalness={0.72} roughness={0.32} />
      </mesh>
      <mesh position={[0, 0, 0.095]}>
        <planeGeometry args={[3.34, 2.08]} />
        <meshStandardMaterial color="#0a292b" metalness={0.35} roughness={0.7} emissive="#052120" emissiveIntensity={0.8} />
      </mesh>
      {pixelLines.map((position) => (
        <mesh key={`vertical-${position}`} position={[position, 0, 0.112]}>
          <boxGeometry args={[0.012, 2.05, 0.008]} />
          <meshBasicMaterial color="#1b6460" transparent opacity={0.34} />
        </mesh>
      ))}
      {pixelLines.slice(0, 6).map((_, index) => {
        const position = -0.88 + index * 0.36;
        return (
          <mesh key={`horizontal-${position}`} position={[0, position, 0.113]}>
            <boxGeometry args={[3.32, 0.012, 0.008]} />
            <meshBasicMaterial color="#1b6460" transparent opacity={0.34} />
          </mesh>
        );
      })}
      {strikes.map((strike, index) => (
        <group key={index} position={strike.position} rotation={strike.rotation}>
          <mesh>
            <boxGeometry args={[strike.length, 0.055, 0.045]} />
            <meshBasicMaterial color="#5eead4" toneMapped={false} />
          </mesh>
          <pointLight color="#2dd4bf" intensity={0.9} distance={1.6} />
        </group>
      ))}
      <mesh position={[-1.52, -1.08, -0.08]}>
        <boxGeometry args={[0.38, 0.24, 0.28]} />
        <meshStandardMaterial color="#14272a" metalness={0.85} roughness={0.25} />
      </mesh>
    </group>
  );
}

export default function DetectorHero() {
  return (
    <Canvas dpr={[1, 1.5]} frameloop="demand" camera={{ position: [0, 0.15, 5.4], fov: 39 }} gl={{ antialias: true, alpha: true, powerPreference: 'low-power', toneMapping: THREE.ACESFilmicToneMapping }}>
      <ambientLight intensity={0.58} />
      <directionalLight position={[3, 4, 5]} intensity={2.3} color="#ccfbf1" />
      <directionalLight position={[-4, -2, 2]} intensity={0.9} color="#0f766e" />
      <DetectorAssembly />
    </Canvas>
  );
}
