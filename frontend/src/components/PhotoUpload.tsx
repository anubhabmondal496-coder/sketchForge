import React, { useRef, useState, useCallback, useEffect } from 'react';

interface PhotoUploadProps {
  onPhotoSelected: (file: File | null) => void;
  selectedPhoto: File | null;
  disabled?: boolean;
}

const SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
const SUPPORTED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export const PhotoUpload: React.FC<PhotoUploadProps> = ({
  onPhotoSelected,
  selectedPhoto,
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Sync preview URL with selectedPhoto
  useEffect(() => {
    if (!selectedPhoto) {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
      }
      return;
    }

    const objectUrl = URL.createObjectURL(selectedPhoto);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedPhoto]);

  const validateAndSelectFile = useCallback(
    (file: File) => {
      setErrorMessage(null);

      // 1. Size validation
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setErrorMessage(
          `Image size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds 10 MB limit. Please select a smaller photo.`
        );
        return;
      }

      // 2. Format validation (MIME and extension)
      const nameLower = file.name.toLowerCase();
      const hasValidExt = SUPPORTED_EXTENSIONS.some((ext) => nameLower.endsWith(ext));
      const hasValidMime = file.type ? SUPPORTED_MIME_TYPES.includes(file.type) : true;

      if (!hasValidExt && !hasValidMime) {
        setErrorMessage(
          'Unsupported file format. Please upload a JPG, JPEG, PNG, or WEBP image.'
        );
        return;
      }

      onPhotoSelected(file);
    },
    [onPhotoSelected]
  );

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !isDragging) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndSelectFile(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      validateAndSelectFile(file);
    }
  };

  const handleTriggerBrowse = () => {
    if (disabled) return;
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  const handleRemove = () => {
    setErrorMessage(null);
    onPhotoSelected(null);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: '380px',
        padding: '16px',
        boxSizing: 'border-box',
        background: 'var(--bg-app)',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={handleFileInputChange}
      />

      <div
        style={{
          fontSize: '12px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          color: 'var(--text-muted)',
          marginBottom: '10px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span>Upload a reference photo</span>
        <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'none' }}>
          JPG / PNG / WEBP &bull; Max 10MB
        </span>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div
          style={{
            padding: '8px 12px',
            marginBottom: '12px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '4px',
            color: '#fca5a5',
            fontSize: '12px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              background: 'transparent',
              border: 'none',
              color: '#fca5a5',
            }}
          >
            &times;
          </button>
        </div>
      )}

      {selectedPhoto && previewUrl ? (
        /* Image Preview State */
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '12px',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            background: 'var(--bg-panel)',
            padding: '16px',
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              position: 'relative',
              maxWidth: '100%',
              maxHeight: '260px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '4px',
              overflow: 'hidden',
              background: '#0d0f12',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <img
              src={previewUrl}
              alt="Reference photo preview"
              style={{
                maxWidth: '100%',
                maxHeight: '260px',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              maxWidth: '380px',
              fontSize: '12px',
              color: 'var(--text-muted)',
            }}
          >
            <span
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: '220px',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
              }}
              title={selectedPhoto.name}
            >
              {selectedPhoto.name} ({(selectedPhoto.size / 1024).toFixed(0)} KB)
            </span>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={handleTriggerBrowse}
                disabled={disabled}
                style={{
                  fontSize: '12px',
                  padding: '4px 10px',
                }}
              >
                Replace
              </button>
              <button
                type="button"
                onClick={handleRemove}
                disabled={disabled}
                style={{
                  fontSize: '12px',
                  padding: '4px 10px',
                  color: 'var(--status-red)',
                  borderColor: 'rgba(239, 68, 68, 0.3)',
                }}
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Empty Dropzone State */
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleTriggerBrowse}
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            border: `2px dashed ${
              isDragging ? 'var(--accent)' : 'var(--border-strong)'
            }`,
            borderRadius: '4px',
            background: isDragging ? 'var(--accent-subtle)' : 'var(--bg-panel)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            padding: '24px',
            transition: 'border-color 0.15s ease, background-color 0.15s ease',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '4px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '12px',
              color: 'var(--text-muted)',
            }}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          </div>

          <div
            style={{
              fontSize: '14px',
              fontWeight: 500,
              color: 'var(--text-main)',
              marginBottom: '4px',
            }}
          >
            Drop image here
          </div>

          <div
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginBottom: '14px',
            }}
          >
            or <span style={{ color: 'var(--accent)', textDecoration: 'underline' }}>Browse files</span>
          </div>

          <div
            style={{
              fontSize: '11px',
              color: 'var(--text-dim)',
            }}
          >
            JPG, PNG, or WEBP up to 10 MB
          </div>
        </div>
      )}
    </div>
  );
};
