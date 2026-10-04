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

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
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
    global.fetch = vi.fn().mockImplementation(async (_url, opts) => {
      capturedBody = opts.body;
      return {
        ok: true,
        json: async () => mockSpec,
      };
    });

    const dummyBlob = new Blob(['test-image'], { type: 'image/png' });
    const result = await analyzeSketch(dummyBlob, 'wooden chair');

    expect(result.object).toBe('chair');
    expect(capturedBody).toBeInstanceOf(FormData);
  });

  it('startGeneration initiates tracked async job', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'job-987', status: 'queued' }),
    } as any);

    const dummyBlob = new Blob(['test-image'], { type: 'image/png' });
    const result = await startGeneration(dummyBlob, 'table');
    expect(result.job_id).toBe('job-987');
    expect(result.status).toBe('queued');
  });

  it('pollJob retrieves real-time status and telemetry', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        job_id: 'job-987',
        status: 'completed',
        generation_time: 12.4,
        model_url: '/model/job-987',
      }),
    } as any);

    const result = await pollJob('job-987');
    expect(result.status).toBe('completed');
    expect(result.generation_time).toBe(12.4);
  });
});
