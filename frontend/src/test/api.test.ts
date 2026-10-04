import { describe, it, expect, vi, beforeEach } from 'vitest';
import { checkHealth, analyzeSketch, startGeneration, pollJob } from '../services/api';

describe('SketchForge API Service Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('checkHealth returns operational status', async () => {
    const mockHealth = {
      status: 'ok',
      gpu: true,
      device: 'NVIDIA RTX 4000 Ada',
      models: { gemma: true, tripo: true },
      mock_mode: false,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockHealth),
      json: async () => mockHealth,
    } as any);

    const result = await checkHealth();
    expect(result.status).toBe('ok');
    expect(result.gpu).toBe(true);
    expect(result.models.gemma).toBe(true);
  });

  it('analyzeSketch sends FormData with image and description', async () => {
    const mockSpec = {
      object: 'chair',
      confidence: 0.95,
      style: 'modern',
      material: 'wood',
      components: ['seat', 'backrest', 'legs'],
      geometry: { width: 0.5, height: 0.9 },
    };

    let capturedBody: FormData | null = null;
    globalThis.fetch = vi.fn().mockImplementation(async (_url, opts) => {
      capturedBody = opts.body;
      return {
        ok: true,
        text: async () => JSON.stringify(mockSpec),
        json: async () => mockSpec,
      };
    });

    const dummyBlob = new Blob(['test-image'], { type: 'image/png' });
    const result = await analyzeSketch(dummyBlob, 'wooden chair');

    expect(result.object).toBe('chair');
    expect(capturedBody).toBeInstanceOf(FormData);
  });

  it('startGeneration initiates tracked async job', async () => {
    const jobData = { job_id: 'job-987', status: 'queued' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(jobData),
      json: async () => jobData,
    } as any);

    const dummyBlob = new Blob(['test-image'], { type: 'image/png' });
    const result = await startGeneration(dummyBlob, 'table');
    expect(result.job_id).toBe('job-987');
    expect(result.status).toBe('queued');
  });

  it('generateFromPhoto submits photo and description to photo generation endpoint', async () => {
    let capturedUrl = '';
    let capturedBody: FormData | null = null;
    const photoJob = { job_id: 'photo-job-123', status: 'processing' };

    globalThis.fetch = vi.fn().mockImplementation(async (url, opts) => {
      capturedUrl = url;
      capturedBody = opts.body;
      return {
        ok: true,
        text: async () => JSON.stringify(photoJob),
        json: async () => photoJob,
      };
    });

    const dummyFile = new File(['fake-photo-data'], 'office_chair.jpg', { type: 'image/jpeg' });
    const { generateFromPhoto } = await import('../services/api');
    const result = await generateFromPhoto(dummyFile, 'modern ergonomic office chair');

    expect(capturedUrl).toContain('/api/generate-from-photo');
    expect(result.job_id).toBe('photo-job-123');
    expect(result.status).toBe('processing');
    expect(capturedBody).toBeInstanceOf(FormData);
  });

  it('pollJob retrieves real-time status and telemetry', async () => {
    const pollData = {
      job_id: 'job-987',
      status: 'completed',
      generation_time: 12.4,
      model_url: '/model/job-987',
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(pollData),
      json: async () => pollData,
    } as any);

    const result = await pollJob('job-987');
    expect(result.status).toBe('completed');
    expect(result.generation_time).toBe(12.4);
  });

  it('searchAssets queries asset search endpoint', async () => {
    const mockResults = {
      results: [
        {
          provider: 'sketchfab',
          id: 'sk_123',
          name: 'Office Chair',
          score: 0.94,
          downloadable: true,
        },
      ],
      total: 1,
      best_match: { provider: 'sketchfab', id: 'sk_123', name: 'Office Chair', score: 0.94, downloadable: true },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockResults),
      json: async () => mockResults,
    } as any);

    const res = await (await import('../services/api')).searchAssets({ object_type: 'chair' });
    expect(res.results.length).toBe(1);
    expect(res.results[0].name).toBe('Office Chair');
    expect(res.best_match?.score).toBe(0.94);
  });

  it('importAsset downloads and activates asset model', async () => {
    const mockImport = {
      success: true,
      asset_id: 'sk_123',
      provider: 'sketchfab',
      model_url: '/api/assets/sketchfab/sk_123/model.glb',
      cached: false,
      metadata: {
        source: 'Sketchfab',
        provider: 'sketchfab',
        asset_id: 'sk_123',
        author: 'Artist',
        license: 'CC BY',
      },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockImport),
      json: async () => mockImport,
    } as any);

    const res = await (await import('../services/api')).importAsset({
      provider: 'sketchfab',
      id: 'sk_123',
      name: 'Office Chair',
      score: 0.94,
      downloadable: true,
    });
    expect(res.success).toBe(true);
    expect(res.model_url).toContain('sk_123');
    expect(res.metadata.license).toBe('CC BY');
  });
});
