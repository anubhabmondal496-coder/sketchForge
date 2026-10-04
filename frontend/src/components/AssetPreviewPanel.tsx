import React from 'react';
import { AssetSearchResult } from '../types/scene';

interface AssetPreviewPanelProps {
  results: AssetSearchResult[];
  selectedAssetId: string | null;
  onSelectAsset: (asset: AssetSearchResult) => void;
  onUseAsset: (asset: AssetSearchResult) => void;
  isLoading?: boolean;
}

export const AssetPreviewPanel: React.FC<AssetPreviewPanelProps> = ({
  results,
  selectedAssetId,
  onSelectAsset,
  onUseAsset,
  isLoading = false,
}) => {
  if (!results || results.length === 0) return null;

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--text-muted)',
            }}
          >
            Available 3D Assets ({results.length})
          </span>
          <span
            style={{
              fontSize: '10px',
              background: 'rgba(59, 130, 246, 0.15)',
              color: '#60a5fa',
              padding: '2px 6px',
              borderRadius: '10px',
              fontWeight: 600,
            }}
          >
            Auto Match: {Math.round((results[0]?.score || 0) * 100)}%
          </span>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: '10px',
          maxHeight: '260px',
          overflowY: 'auto',
          paddingRight: '4px',
        }}
      >
        {results.map((asset, index) => {
          const isBestMatch = index === 0;
          const isSelected = selectedAssetId === asset.id;
          const matchPercent = Math.round((asset.score || 0) * 100);

          return (
            <div
              key={`${asset.provider}_${asset.id}`}
              onClick={() => onSelectAsset(asset)}
              style={{
                background: isSelected ? 'var(--bg-input)' : 'var(--bg-panel)',
                border: isSelected
                  ? '1.5px solid var(--accent)'
                  : isBestMatch
                  ? '1px solid rgba(59, 130, 246, 0.4)'
                  : '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                cursor: 'pointer',
                position: 'relative',
                transition: 'all 0.2s ease',
              }}
            >
              {isBestMatch && (
                <div
                  style={{
                    position: 'absolute',
                    top: '6px',
                    right: '6px',
                    background: 'var(--accent)',
                    color: '#fff',
                    fontSize: '9px',
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    textTransform: 'uppercase',
                  }}
                >
                  Best Match
                </div>
              )}

              {/* Title & Provider */}
              <div style={{ paddingRight: isBestMatch ? '60px' : '0' }}>
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: 'var(--text-main)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={asset.name}
                >
                  {asset.name}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
                  Provider: <strong style={{ color: 'var(--text-muted)' }}>{asset.provider.toUpperCase()}</strong>
                </div>
              </div>

              {/* Details & Author */}
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div>Author: {asset.author || 'Open Contributor'}</div>
                <div>License: <span style={{ color: '#34d399' }}>{asset.license || 'CC BY'}</span></div>
                <div>Relevance: <strong style={{ color: '#60a5fa' }}>{matchPercent}%</strong></div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '6px', marginTop: 'auto', paddingTop: '4px' }}>
                <button
                  type="button"
                  disabled={isLoading || !asset.downloadable}
                  onClick={(e) => {
                    e.stopPropagation();
                    onUseAsset(asset);
                  }}
                  style={{
                    flex: 1,
                    fontSize: '11px',
                    padding: '4px 8px',
                    background: isBestMatch ? 'var(--accent)' : 'var(--bg-surface)',
                    borderColor: isBestMatch ? 'var(--accent)' : 'var(--border-subtle)',
                    color: isBestMatch ? '#fff' : 'var(--text-main)',
                    fontWeight: 600,
                  }}
                >
                  {isLoading && isSelected ? 'Loading...' : 'Use this model'}
                </button>

                {asset.preview_url && (
                  <a
                    href={asset.preview_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      fontSize: '11px',
                      padding: '4px 8px',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: 'var(--text-dim)',
                      textDecoration: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                    title="View Source on Provider"
                  >
                    Source
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
