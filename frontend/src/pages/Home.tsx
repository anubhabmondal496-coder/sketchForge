import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from '../components/Header';
import { SketchCanvas, SketchCanvasHandle } from '../components/SketchCanvas';
import { DescriptionInput } from '../components/DescriptionInput';
import { GenerateButton } from '../components/GenerateButton';
import { GenerationStatus } from '../components/GenerationStatus';
import { ModelViewer } from '../components/ModelViewer';
import { SceneSpecPanel } from '../components/SceneSpecPanel';
import { RefinementInput } from '../components/RefinementInput';
import { LegalModal } from '../components/LegalModal';
import { AssetPreviewPanel } from '../components/AssetPreviewPanel';
import {
  checkHealth,
  startGeneration,
  pollJob,
  refineScene,
  getModelFileUrl,
  importAsset,
} from '../services/api';
import {
  HealthResponse,
  JobStatus,
  SceneSpec,
  RefinementHistoryEntry,
  AssetSearchResult,
  AssetMetadata,
} from '../types/scene';

export const Home: React.FC = () => {
  // Legal modal state
  const [legalModalType, setLegalModalType] = useState<'privacy' | 'terms' | null>(null);

  // Backend health state
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Canvas & Prompt input state
  const canvasRef = useRef<SketchCanvasHandle | null>(null);
  const [hasStrokes, setHasStrokes] = useState<boolean>(false);
  const [description, setDescription] = useState<string>('');
  const [lastImageBlob, setLastImageBlob] = useState<Blob | null>(null);

  const handleStrokeChange = useCallback((has: boolean) => {
    setHasStrokes(has);
  }, []);

  // Active generation / job state
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [stageMessage, setStageMessage] = useState<string>('');
  const [generationTime, setGenerationTime] = useState<number | undefined>(undefined);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // Scene & Model state
  const [currentSceneSpec, setCurrentSceneSpec] = useState<SceneSpec | null>(null);
  const [currentModelUrl, setCurrentModelUrl] = useState<string | null>(null);
  const [currentSourceType, setCurrentSourceType] = useState<'asset_search' | 'ai_generation'>('ai_generation');
  const [currentAssetMetadata, setCurrentAssetMetadata] = useState<AssetMetadata | null>(null);
  const [searchResults, setSearchResults] = useState<AssetSearchResult[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [isImportingAsset, setIsImportingAsset] = useState<boolean>(false);
  const [history, setHistory] = useState<RefinementHistoryEntry[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(1);

  // Check backend health
  const refreshHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await checkHealth();
      setHealth(data);
    } catch (err: any) {
      setHealthError(err.message || 'AI backend unavailable');
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  // Polling helper
  const pollJobStatus = async (
    jobId: string,
    refinementText?: string,
    previousVersion?: number
  ) => {
    const pollInterval = 1000;
    const maxPollAttempts = 120; // 2 minutes max
    let attempts = 0;

    const poll = async () => {
      if (attempts >= maxPollAttempts) {
        setPipelineError('Generation timed out. The GPU server may be under high load.');
        setJobStatus('failed');
        return;
      }

      try {
        const job = await pollJob(jobId);
        setJobStatus(job.status);
        if (job.stage_message) setStageMessage(job.stage_message);

        if (job.search_results && job.search_results.length > 0) {
          setSearchResults(job.search_results);
        }

        if (job.status === 'completed' || job.status === 'ready') {
          const modelUrl = job.model_url
            ? (job.model_url.startsWith('http') ? job.model_url : getModelFileUrl(job.job_id))
            : getModelFileUrl(job.job_id);

          const spec = job.scene_spec || null;
          setCurrentSceneSpec(spec);
          setCurrentModelUrl(modelUrl);
          setCurrentSourceType(job.source_type || 'ai_generation');
          setCurrentAssetMetadata(job.asset_metadata || null);
          if (job.asset_metadata) {
            setSelectedAssetId(job.asset_metadata.asset_id);
          }
          if (job.generation_time) setGenerationTime(job.generation_time);

          const nextVersion = (previousVersion || 0) + 1;
          setCurrentVersion(nextVersion);

          if (spec) {
            setHistory((prev) => [
              ...prev,
              {
                version: nextVersion,
                scene_spec: spec,
                model_url: modelUrl,
                refinement_prompt: refinementText,
                generation_time: job.generation_time,
                timestamp: new Date().toISOString(),
                source_type: job.source_type || 'ai_generation',
                asset_metadata: job.asset_metadata || undefined,
              },
            ]);
          }
        } else if (job.status === 'failed') {
          setPipelineError(job.error || 'Generation failed. Check server logs.');
        } else {
          // Keep polling
          attempts++;
          setTimeout(poll, pollInterval);
        }
      } catch (err: any) {
        setPipelineError(err.message || 'Lost connection to generation backend.');
        setJobStatus('failed');
      }
    };

    poll();
  };

  // Step 1 -> Generate 3D Model
  const handleGenerate = async () => {
    if (!canvasRef.current) return;
    setPipelineError(null);

    const imageBlob = await canvasRef.current.getBlob();
    if (!imageBlob || canvasRef.current.isEmpty()) {
      setPipelineError('Canvas is empty. Draw a rough sketch before generating.');
      return;
    }

    setLastImageBlob(imageBlob);
    setJobStatus('queued');
    setStageMessage('Initiating generation job...');
    setGenerationTime(undefined);

    try {
      const response = await startGeneration(imageBlob, description);
      setActiveJobId(response.job_id);
      setHistory([]);
      pollJobStatus(response.job_id, undefined, 0);
    } catch (err: any) {
      setPipelineError(err.message || 'Failed to submit generation job.');
      setJobStatus('failed');
    }
  };

  // Step 3 -> Refine existing 3D Model
  const handleRefine = async (refinementText: string) => {
    if (!currentSceneSpec) return;
    setPipelineError(null);
    setJobStatus('queued');
    setStageMessage('Submitting refinement...');

    try {
      const response = await refineScene(
        currentSceneSpec,
        refinementText,
        lastImageBlob
      );
      setActiveJobId(response.job_id);
      pollJobStatus(response.job_id, refinementText, currentVersion);
    } catch (err: any) {
      setPipelineError(err.message || 'Failed to start refinement job.');
      setJobStatus('failed');
    }
  };

  const handleSelectVersion = (version: number) => {
    const entry = history.find((h) => h.version === version);
    if (entry) {
      setCurrentVersion(version);
      setCurrentSceneSpec(entry.scene_spec);
      if (entry.model_url) setCurrentModelUrl(entry.model_url);
      if (entry.generation_time) setGenerationTime(entry.generation_time);
      setCurrentSourceType(entry.source_type || 'ai_generation');
      setCurrentAssetMetadata(entry.asset_metadata || null);
    }
  };

  // Step 8 -> Manual selection of an asset from search results
  const handleUseAsset = async (asset: AssetSearchResult) => {
    setIsImportingAsset(true);
    setSelectedAssetId(asset.id);
    setJobStatus('importing');
    setStageMessage(`Importing ${asset.name} from ${asset.provider}...`);

    try {
      const res = await importAsset(asset);
      if (res.success) {
        setCurrentModelUrl(res.model_url);
        setCurrentSourceType('asset_search');
        setCurrentAssetMetadata(res.metadata);
        setJobStatus('completed');
        setStageMessage(`Model ready: ${asset.name}`);

        const nextVersion = currentVersion + 1;
        setCurrentVersion(nextVersion);
        if (currentSceneSpec) {
          setHistory((prev) => [
            ...prev,
            {
              version: nextVersion,
              scene_spec: currentSceneSpec,
              model_url: res.model_url,
              refinement_prompt: `Imported asset: ${asset.name}`,
              generation_time: 0.8,
              timestamp: new Date().toISOString(),
              source_type: 'asset_search',
              asset_metadata: res.metadata,
            },
          ]);
        }
      }
    } catch (err: any) {
      setPipelineError(err.message || 'Failed to import 3D asset.');
      setJobStatus('failed');
    } finally {
      setIsImportingAsset(false);
    }
  };

  const handleSelectAsset = (asset: AssetSearchResult) => {
    setSelectedAssetId(asset.id);
  };

  const isGenerating =
    jobStatus !== null && jobStatus !== 'completed' && jobStatus !== 'failed';

  return (
    <div className="app-container">
      <Header
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
        onRefreshHealth={refreshHealth}
      />

      <main className="main-workspace">
        {/* Left Column: Sketch & Description (Input Forge) */}
        <div className="column-card">
          <div className="panel-header">
            <div className="panel-title">
              <span className="step-badge">1</span>
              <span>Sketch &amp; Prompt</span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              2D User Input
            </span>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* Sketch Canvas */}
            <div style={{ flex: 1, minHeight: '380px' }}>
              <SketchCanvas
                ref={canvasRef}
                onStrokeChange={handleStrokeChange}
              />
            </div>

            {/* Input Controls */}
            <div
              style={{
                padding: '16px',
                borderTop: '1px solid var(--border-subtle)',
                background: 'var(--bg-panel)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <DescriptionInput
                value={description}
                onChange={setDescription}
                disabled={isGenerating}
              />

              <GenerateButton
                onClick={handleGenerate}
                disabled={!hasStrokes}
                isLoading={isGenerating}
              />

              <GenerationStatus
                jobId={activeJobId}
                status={jobStatus}
                stageMessage={stageMessage}
                error={pipelineError}
                generationTime={generationTime}
                onDismissError={() => setPipelineError(null)}
              />
            </div>
          </div>
        </div>

        {/* Right Column: 3D Mesh & Multimodal Reasoning (Output Forge) */}
        <div className="column-card">
          <div className="panel-header">
            <div className="panel-title">
              <span className="step-badge">2</span>
              <span>Reconstruction &amp; Refinement</span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              Gemma 4 E4B + TripoSR
            </span>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* Three.js 3D Viewer */}
            <div style={{ flex: 1, minHeight: '380px', position: 'relative' }}>
              <ModelViewer
                modelUrl={currentModelUrl}
                generationTime={generationTime}
                assetMetadata={currentAssetMetadata}
                sourceType={currentSourceType}
              />
            </div>

            {/* Asset Selection Preview Panel (Step 8) */}
            {searchResults && searchResults.length > 0 && (
              <div style={{ padding: '0 16px', background: 'var(--bg-panel)' }}>
                <AssetPreviewPanel
                  results={searchResults}
                  selectedAssetId={selectedAssetId}
                  onSelectAsset={handleSelectAsset}
                  onUseAsset={handleUseAsset}
                  isLoading={isImportingAsset}
                />
              </div>
            )}

            {/* Reasoning & Refinement Footer */}
            <div
              style={{
                padding: '16px',
                borderTop: '1px solid var(--border-subtle)',
                background: 'var(--bg-panel)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <SceneSpecPanel
                sceneSpec={currentSceneSpec}
                version={currentVersion}
              />

              <RefinementInput
                onRefine={handleRefine}
                isLoading={isGenerating}
                disabled={!currentSceneSpec}
                history={history}
                currentVersion={currentVersion}
                onSelectVersion={handleSelectVersion}
                isStaticAsset={currentSourceType === 'asset_search'}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer Info */}
      <footer
        style={{
          padding: '8px 20px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-panel)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: 'var(--text-dim)',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div>
          SketchForge &bull; Multimodal reasoning by Google Gemma 4 E4B &bull; 3D reconstruction by Stability AI TripoSR
        </div>
        <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
          <span>GLB Mesh Export</span>
          <span>DigitalOcean RTX 4000 Ada</span>
          <button
            type="button"
            onClick={() => setLegalModalType('privacy')}
            style={{
              padding: '0',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '11px',
            }}
          >
            Privacy
          </button>
          <button
            type="button"
            onClick={() => setLegalModalType('terms')}
            style={{
              padding: '0',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '11px',
            }}
          >
            Terms
          </button>
        </div>
      </footer>

      <LegalModal
        isOpen={legalModalType !== null}
        type={legalModalType}
        onClose={() => setLegalModalType(null)}
      />
    </div>
  );
};
