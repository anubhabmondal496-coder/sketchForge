import React, { useState } from 'react';
import { SceneSpec } from '../types/scene';

interface SceneSpecPanelProps {
  sceneSpec: SceneSpec | null;
  version?: number;
}

export const SceneSpecPanel: React.FC<SceneSpecPanelProps> = ({ sceneSpec, version = 1 }) => {
  const [showRawJson, setShowRawJson] = useState(false);

  if (!sceneSpec) {
    return (
      <div
        style={{
          padding: '16px',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '4px',
          color: 'var(--text-dim)',
          fontSize: '12px',
          textAlign: 'center',
        }}
      >
        Awaiting sketch analysis by Gemma 4 E4B...
      </div>
    );
  }

  const confidencePct = Math.round(sceneSpec.confidence * 100);

  return (
    <div
      style={{
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '4px',
        overflow: 'hidden',
        fontSize: '12px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 600, color: 'var(--text-main)', textTransform: 'uppercase' }}>
            SceneSpec
          </span>
          <span
            style={{
              padding: '1px 6px',
              fontSize: '10px',
              fontWeight: 700,
              background: 'var(--accent-subtle)',
              color: 'var(--accent)',
              borderRadius: '2px',
            }}
          >
            v{version}
          </span>
        </div>

        <button
          onClick={() => setShowRawJson(!showRawJson)}
          style={{
            padding: '2px 6px',
            fontSize: '11px',
            background: 'transparent',
            borderColor: 'var(--border-subtle)',
            color: 'var(--text-muted)',
          }}
        >
          {showRawJson ? 'Structured View' : 'Raw JSON'}
        </button>
      </div>

      {showRawJson ? (
        <pre
          style={{
            padding: '12px',
            margin: 0,
            background: 'var(--bg-input)',
            color: '#a5b4fc',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            maxHeight: '220px',
            overflow: 'auto',
          }}
        >
          {JSON.stringify(sceneSpec, null, 2)}
        </pre>
      ) : (
        <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
            <div style={{ background: 'var(--bg-input)', padding: '6px 8px', borderRadius: '3px' }}>
              <div style={{ color: 'var(--text-dim)', fontSize: '10px', textTransform: 'uppercase' }}>Object</div>
              <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{sceneSpec.object}</div>
            </div>
            <div style={{ background: 'var(--bg-input)', padding: '6px 8px', borderRadius: '3px' }}>
              <div style={{ color: 'var(--text-dim)', fontSize: '10px', textTransform: 'uppercase' }}>Confidence</div>
              <div style={{ fontWeight: 600, color: confidencePct > 70 ? 'var(--status-green)' : 'var(--status-amber)' }}>
                {confidencePct}%
              </div>
            </div>
            <div style={{ background: 'var(--bg-input)', padding: '6px 8px', borderRadius: '3px' }}>
              <div style={{ color: 'var(--text-dim)', fontSize: '10px', textTransform: 'uppercase' }}>Material</div>
              <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{sceneSpec.material || 'standard'}</div>
            </div>
          </div>

          {sceneSpec.style && (
            <div style={{ display: 'flex', gap: '6px' }}>
              <span style={{ color: 'var(--text-dim)' }}>Style:</span>
              <span style={{ color: 'var(--text-muted)' }}>{sceneSpec.style}</span>
            </div>
          )}

          {sceneSpec.components && sceneSpec.components.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-dim)' }}>Components:</span>
              {sceneSpec.components.map((comp, idx) => (
                <span
                  key={idx}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    padding: '1px 6px',
                    borderRadius: '3px',
                    color: 'var(--text-muted)',
                    fontSize: '11px',
                  }}
                >
                  {comp}
                </span>
              ))}
            </div>
          )}

          {sceneSpec.geometry && Object.keys(sceneSpec.geometry).length > 0 && (
            <div
              style={{
                background: 'var(--bg-input)',
                padding: '6px 8px',
                borderRadius: '3px',
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap',
                fontSize: '11px',
              }}
            >
              <span style={{ color: 'var(--text-dim)' }}>Geometry:</span>
              {Object.entries(sceneSpec.geometry).map(([k, v]) => (
                <span key={k} style={{ color: 'var(--text-muted)' }}>
                  {k}: <strong style={{ color: 'var(--text-main)' }}>{v}m</strong>
                </span>
              ))}
            </div>
          )}

          {sceneSpec.generation_prompt && (
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontStyle: 'italic', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
              &ldquo;{sceneSpec.generation_prompt}&rdquo;
            </div>
          )}
        </div>
      )}
    </div>
  );
};
