import React, { useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';

const Shield = () => {
  const meshRef = useRef<THREE.Mesh>(null);
  const { mouse } = useThree();

  useFrame((_state, delta) => {
    if (meshRef.current) {
      // Base rotation
      meshRef.current.rotation.y += delta * 0.2;
      // Mouse reactive subtle tilt
      const targetRotationX = (mouse.y * Math.PI) / 8;
      const targetRotationY = (mouse.x * Math.PI) / 8;
      
      meshRef.current.rotation.x += (targetRotationX - meshRef.current.rotation.x) * 0.1;
      // We add to the base y rotation instead of replacing it
      meshRef.current.rotation.y += (targetRotationY) * 0.02;
    }
  });

  return (
    <Float
      speed={2} // Animation speed
      rotationIntensity={0.5} // XYZ rotation intensity
      floatIntensity={0.5} // Up/down float intensity
    >
      <mesh ref={meshRef} scale={1.5}>
        <octahedronGeometry args={[1, 0]} />
        <meshStandardMaterial 
          color="#2DD4BF" 
          wireframe={true} 
          transparent 
          opacity={0.8}
        />
        
        {/* Inner solid core */}
        <mesh scale={0.7}>
          <octahedronGeometry args={[1, 0]} />
          <meshStandardMaterial 
            color="#0B0F14" 
            metalness={0.8}
            roughness={0.2}
          />
        </mesh>
      </mesh>
    </Float>
  );
};

export const Hero3D: React.FC = () => {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none opacity-40 overflow-hidden">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} color="#2DD4BF" />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} color="#F5A524" />
        <Shield />
      </Canvas>
    </div>
  );
};
