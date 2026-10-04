import React from 'react';

interface LegalModalProps {
  isOpen: boolean;
  type: 'privacy' | 'terms' | null;
  onClose: () => void;
}

export const LegalModal: React.FC<LegalModalProps> = ({ isOpen, type, onClose }) => {
  if (!isOpen || !type) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-strong)',
          borderRadius: '6px',
          maxWidth: '640px',
          width: '100%',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 16px',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <h2 style={{ fontSize: '15px', fontWeight: 600, margin: 0 }}>
            {type === 'privacy' ? 'Privacy Policy' : 'Terms of Service'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '2px 8px',
              fontSize: '12px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
            }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            padding: '16px',
            overflowY: 'auto',
            fontSize: '13px',
            lineHeight: '1.6',
            color: 'var(--text-muted)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {type === 'privacy' ? (
            <>
              <p>
                <strong>Effective Date:</strong> October 2026
              </p>
              <p>
                <strong>SketchForge Data Processing:</strong> SketchForge is an AI-assisted 3D geometry prototyping tool.
                When you create and submit a sketch or text description, the image and prompt data are transmitted securely
                to the SketchForge backend server for multimodal interpretation (via Gemma 4 E4B) and 3D mesh reconstruction (via TripoSR).
              </p>
              <p>
                <strong>Storage &amp; Retention:</strong> Uploaded sketches and resulting 3D geometry files (GLB) are stored in a
                temporary workspace on the processing server to facilitate real-time iterative refinement. Generation directories
                are periodically pruned by the automated server job lifecycle. We do not sell your sketches or personal data.
              </p>
              <p>
                <strong>Security:</strong> All communication between the web client and inference backend is conducted over encrypted
                HTTPS connections. API credentials and model tokens reside exclusively on the server side.
              </p>
            </>
          ) : (
            <>
              <p>
                <strong>Terms of Service:</strong> By accessing or using SketchForge, you agree to these Terms.
              </p>
              <p>
                <strong>Generative Prototyping Disclaimer:</strong> SketchForge produces experimental 3D geometry from 2D sketches.
                A single 2D sketch does not contain complete backside geometry; generated models are generative approximations and
                are not guaranteed to be dimensionally accurate or manufacturing/CAD ready.
              </p>
              <p>
                <strong>Acceptable Use:</strong> You agree not to upload harmful, abusive, illegal, or infringing content.
                The application is provided &ldquo;as is&rdquo; without warranties of any kind.
              </p>
            </>
          )}
        </div>

        <div
          style={{
            padding: '10px 16px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <button type="button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};
