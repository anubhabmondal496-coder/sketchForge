import { HealthResponse, JobResponse, SceneSpec } from '../types/scene';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  statusCode?: number;
  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `Request failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMessage = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Non-JSON error body fallback
      const text = await response.text();
      if (text) errorMessage = text.slice(0, 200);
    }
    throw new ApiError(errorMessage, response.status);
  }
  return response.json() as Promise<T>;
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return await handleResponse<HealthResponse>(res);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('AI backend is currently unreachable. Ensure the backend server is running.');
  }
}

export async function analyzeSketch(imageBlob: Blob, description?: string): Promise<SceneSpec> {
  const formData = new FormData();
  formData.append('image', imageBlob, 'sketch.png');
  if (description && description.trim()) {
    formData.append('description', description.trim());
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<SceneSpec>(res);
}

export async function startGeneration(
  imageBlob: Blob,
  description?: string
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append('image', imageBlob, 'sketch.png');
  if (description && description.trim()) {
    formData.append('description', description.trim());
  }

  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<{ job_id: string; status: string }>(res);
}

export async function pollJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${API_BASE}/job/${encodeURIComponent(jobId)}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });
  return handleResponse<JobResponse>(res);
}

export function getModelFileUrl(jobId: string): string {
  return `${API_BASE}/model/${encodeURIComponent(jobId)}`;
}

export async function refineScene(
  existingSpec: SceneSpec,
  refinementText: string,
  imageBlob?: Blob | null
): Promise<{ job_id: string; status: string; updated_spec?: SceneSpec }> {
  const formData = new FormData();
  formData.append('existing_spec', JSON.stringify(existingSpec));
  formData.append('refinement', refinementText.trim());
  if (imageBlob) {
    formData.append('image', imageBlob, 'sketch.png');
  }

  const res = await fetch(`${API_BASE}/refine`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<{ job_id: string; status: string; updated_spec?: SceneSpec }>(res);
}

export async function searchAssets(params: {
  object_type?: string;
  search_terms?: string[];
  features?: string[];
  style?: string[];
}): Promise<{ results: import('../types/scene').AssetSearchResult[]; total: number; best_match?: import('../types/scene').AssetSearchResult }> {
  const res = await fetch(`${API_BASE}/api/assets/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return handleResponse(res);
}

export async function importAsset(asset: import('../types/scene').AssetSearchResult): Promise<{
  success: boolean;
  asset_id: string;
  provider: string;
  model_url: string;
  cached: boolean;
  metadata: import('../types/scene').AssetMetadata;
}> {
  const res = await fetch(`${API_BASE}/api/assets/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider: asset.provider,
      asset_id: asset.id,
      download_url: asset.download_url,
      name: asset.name,
      author: asset.author,
      license: asset.license,
      source_url: asset.preview_url,
      attribution: asset.attribution,
    }),
  });
  return handleResponse(res);
}

