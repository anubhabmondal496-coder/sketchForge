import React, { Suspense, useState, useRef, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Center, Grid } from '@react-three/drei';
import * as THREE from 'three';

import { AssetMetadata } from '../types/scene';

interface ModelViewerProps {
  modelUrl: string | null;
  onDownloadGlb?: () => void;
  generationTime?: number;
  assetMetadata?: AssetMetadata | null;
  sourceType?: 'asset_search' | 'ai_generation';
}

interface MeshRendererProps {
  url: string;
  wireframe: boolean;
  onLoaded?: () => void;
  onError?: (err: Error) => void;
}

const MeshRenderer: React.FC<MeshRendererProps> = ({ url, wireframe, onLoaded }) => {
  const gltf = useGLTF(url);

  useEffect(() => {
    if (gltf && gltf.scene) {
      // 1. Calculate bounding box & auto-center/scale model to fit viewport (Step 7)
      const box = new THREE.Box3().setFromObject(gltf.scene);
      const size = new THREE.Vector3();
      box.getSize(size);
      const center = new THREE.Vector3();
      box.getCenter(center);

      // Center model
      gltf.scene.position.x += (gltf.scene.position.x - center.x);
      gltf.scene.position.y += (gltf.scene.position.y - box.min.y); // Ground to y=0
      gltf.scene.position.z += (gltf.scene.position.z - center.z);

      // Auto-scale to normalized bounding size (around 1.8 units)
      const maxDim = Math.max(size.x, size.y, size.z);
      if (maxDim > 0) {
        const targetScale = 1.8 / maxDim;
        gltf.scene.scale.setScalar(targetScale);
      }

      // Preserve materials, textures, shadows
      gltf.scene.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach((m: any) => {
              if ('wireframe' in m) m.wireframe = wireframe;
              m.side = THREE.DoubleSide;
            });
          } else if (mesh.material) {
            const m = mesh.material as any;
            if ('wireframe' in m) m.wireframe = wireframe;
            m.side = THREE.DoubleSide;
          }
        }
      });
      onLoaded?.();
    }
  }, [gltf, wireframe, onLoaded]);

  return (
    <Center top>
      <primitive object={gltf.scene} />
    </Center>
  );
};

class ViewerErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error: any) {
    console.error('Three.js viewer error:', error);
  }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

export const ModelViewer: React.FC<ModelViewerProps> = ({
  modelUrl,
  onDownloadGlb,
  generationTime,
  assetMetadata,
  sourceType,
}) => {
  const [wireframe, setWireframe] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [showAxes, setShowAxes] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const controlsRef = useRef<any>(null);

  // Reset camera view
  const handleResetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  const handleDownload = () => {
    if (!modelUrl) return;
    if (onDownloadGlb) {
      onDownloadGlb();
      return;
    }
    const a = document.createElement('a');
    a.href = modelUrl;
    a.download = 'sketchforge-model.glb';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        background: '#13161c',
      }}
    >
      {/* Viewer controls bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-surface)',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            onClick={() => setWireframe(!wireframe)}
            style={{
              background: wireframe ? 'var(--accent)' : 'var(--bg-input)',
              color: wireframe ? '#fff' : 'var(--text-muted)',
              borderColor: wireframe ? 'var(--accent)' : 'var(--border-subtle)',
              fontSize: '11px',
              padding: '3px 8px',
            }}
            title="Toggle Wireframe mode"
          >
            Wireframe
          </button>
          <button
            type="button"
            onClick={() => setShowGrid(!showGrid)}
            style={{
              background: showGrid ? 'var(--bg-panel)' : 'var(--bg-input)',
              color: showGrid ? 'var(--text-main)' : 'var(--text-dim)',
              fontSize: '11px',
              padding: '3px 8px',
            }}
            title="Toggle Ground Grid"
          >
            Grid
          </button>
          <button
            type="button"
            onClick={() => setShowAxes(!showAxes)}
            style={{
              background: showAxes ? 'var(--bg-panel)' : 'var(--bg-input)',
              color: showAxes ? 'var(--text-main)' : 'var(--text-dim)',
              fontSize: '11px',
              padding: '3px 8px',
            }}
            title="Toggle Axis Helper"
          >
            Axes
          </button>
          <button
            type="button"
            onClick={handleResetCamera}
            style={{ fontSize: '11px', padding: '3px 8px' }}
            title="Reset Camera Angle"
          >
            Reset Camera
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {modelUrl && (
            sourceType === 'asset_search' ? (
              <span
                style={{
                  fontSize: '11px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: '#34d399',
                  padding: '2px 8px',
                  borderRadius: '3px',
                  fontWeight: 600,
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                }}
              >
                Source: 3D Asset
              </span>
            ) : (
              <span
                style={{
                  fontSize: '11px',
                  background: 'rgba(59, 130, 246, 0.15)',
                  color: '#60a5fa',
                  padding: '2px 8px',
                  borderRadius: '3px',
                  fontWeight: 600,
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                }}
              >
                Source: AI Generated
              </span>
            )
          )}
          {generationTime !== undefined && (
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              ({generationTime.toFixed(1)}s)
            </span>
          )}

          <button
            type="button"
            className="primary"
            disabled={!modelUrl}
            onClick={handleDownload}
            style={{
              fontSize: '11px',
              padding: '4px 10px',
              fontWeight: 600,
            }}
          >
            Download GLB
          </button>
        </div>
      </div>

      {/* Legal Attribution Banner if Asset is Imported (Step 2, Legal Rules) */}
      {assetMetadata && (
        <div
          style={{
            padding: '6px 12px',
            background: 'rgba(30, 41, 59, 0.9)',
            borderBottom: '1px solid rgba(59, 130, 246, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: 'var(--text-muted)',
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: '#60a5fa', fontWeight: 600 }}>Source:</span>
            <span>{assetMetadata.provider.toUpperCase()} &bull; Author: <strong>{assetMetadata.author || 'Open Creator'}</strong> &bull; License: <strong style={{ color: '#34d399' }}>{assetMetadata.license || 'CC BY'}</strong></span>
          </div>
          {assetMetadata.source_url && (
            <a
              href={assetMetadata.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#60a5fa', textDecoration: 'underline', fontSize: '10px' }}
            >
              View Attribution
            </a>
          )}
        </div>
      )}

      {/* 3D Canvas Area */}
      <div style={{ position: 'relative', flex: 1, minHeight: '380px', width: '100%' }}>
        {modelUrl && !loadError ? (
          <ViewerErrorBoundary
            key={modelUrl}
            fallback={
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--status-red)',
                  fontSize: '13px',
                }}
              >
                Failed to parse GLB mesh. Try regenerating.
              </div>
            }
          >
            <Canvas
              camera={{ position: [2.5, 2.5, 2.5], fov: 45 }}
              shadows
              style={{ width: '100%', height: '100%' }}
            >
              <color attach="background" args={['#11141a']} />
              <ambientLight intensity={0.8} />
              <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
              <directionalLight position={[-5, -4, -5]} intensity={0.4} />

              {showAxes && <primitive object={new THREE.AxesHelper(1.5)} />}

              {showGrid && (
                <Grid
                  args={[10, 10]}
                  cellSize={0.2}
                  cellThickness={0.8}
                  cellColor="#262c37"
                  sectionSize={1}
                  sectionThickness={1.2}
                  sectionColor="#363e4d"
                  fadeDistance={12}
                  fadeStrength={1}
                />
              )}

              <Suspense
                fallback={
                  <mesh position={[0, 0, 0]}>
                    <boxGeometry args={[0.5, 0.5, 0.5]} />
                    <meshStandardMaterial color="#ea580c" wireframe />
                  </mesh>
                }
              >
                <MeshRenderer
                  url={modelUrl}
                  wireframe={wireframe}
                  onError={(err) => setLoadError(err.message)}
                />
              </Suspense>

              <OrbitControls ref={controlsRef} makeDefault dampingFactor={0.05} />
            </Canvas>
          </ViewerErrorBoundary>
        ) : (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-dim)',
              textAlign: 'center',
              padding: '24px',
            }}
          >
            <div
              style={{
                width: '64px',
                height: '64px',
                border: '1px dashed var(--border-strong)',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '12px',
                color: 'var(--text-muted)',
                fontSize: '20px',
              }}
            >
              3D
            </div>
            <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-muted)' }}>
              Interactive 3D Viewer
            </div>
            <div style={{ fontSize: '12px', marginTop: '4px', maxWidth: '320px' }}>
              Your generated GLB model will load here. You can rotate (drag), zoom (scroll), and inspect wireframes.
            </div>
          </div>
        )}
      </div>

      {/* Viewer tips footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 12px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          fontSize: '11px',
          color: 'var(--text-dim)',
        }}
      >
        <span>Left-click: Rotate &bull; Right-click: Pan &bull; Scroll: Zoom</span>
        <span>GLB format</span>
      </div>
    </div>
  );
};
