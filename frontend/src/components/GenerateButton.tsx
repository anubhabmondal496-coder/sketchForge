import React from 'react';

interface GenerateButtonProps {
  onClick: () => void;
  disabled: boolean;
  isLoading: boolean;
}

export const GenerateButton: React.FC<GenerateButtonProps> = ({
  onClick,
  disabled,
  isLoading,
}) => {
  return (
    <button
      type="button"
      className="primary"
      onClick={onClick}
      disabled={disabled || isLoading}
      style={{
        width: '100%',
        padding: '12px 18px',
        fontSize: '14px',
        fontWeight: 600,
        letterSpacing: '0.02em',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
      }}
    >
      {isLoading ? (
        <>
          <span
            style={{
              width: '14px',
              height: '14px',
              border: '2px solid rgba(255, 255, 255, 0.3)',
              borderTopColor: '#ffffff',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              display: 'inline-block',
            }}
          />
          <span>Processing Pipeline...</span>
        </>
      ) : (
        <span>Generate 3D Model</span>
      )}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </button>
  );
};
