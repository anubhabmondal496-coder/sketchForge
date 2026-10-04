export interface SceneGeometry {
  width?: number;
  depth?: number;
  height?: number;
  back_height?: number;
  [key: string]: number | undefined;
}

export interface SceneSpec {
  object: string;
  confidence: number;
  style?: string;
  material?: string;
  components?: string[];
  geometry?: SceneGeometry;
  generation_prompt?: string;
}

export type JobStatus =
  | 'idle'
  | 'queued'
  | 'analyzing'
  | 'searching'
  | 'found'
  | 'downloading'
  | 'importing'
  | 'generating'
  | 'processing'
  | 'completed'
  | 'ready'
  | 'failed';

export interface AssetMetadata {
  source: string;
  provider: string;
  asset_id: string;
  author?: string;
  license?: string;
  source_url?: string;
  attribution?: string;
  downloaded_at?: string;
}

export interface AssetSearchResult {
  provider: string;
  id: string;
  name: string;
  thumbnail_url?: string;
  preview_url?: string;
  download_url?: string;
  format?: string;
  license?: string;
  author?: string;
  attribution?: string;
  score: number;
  downloadable: boolean;
  metadata?: AssetMetadata;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  stage_message?: string;
  scene_spec?: SceneSpec;
  model_url?: string;
  generation_time?: number;
  error?: string;
  created_at?: string;
  source_type?: 'asset_search' | 'ai_generation';
  asset_metadata?: AssetMetadata;
  search_results?: AssetSearchResult[];
  input_type?: 'sketch' | 'photo';
  detected_objects?: string[];
  needs_clarification?: boolean;
  clarification_question?: string;
}

export interface HealthResponse {
  status: string;
  gpu: boolean;
  device: string;
  models: {
    gemma: boolean;
    tripo: boolean;
  };
  mock_mode: boolean;
  gpu_memory?: {
    total_gb?: number;
    allocated_gb?: number;
    reserved_gb?: number;
  };
}

export interface RefinementHistoryEntry {
  version: number;
  scene_spec: SceneSpec;
  model_url?: string;
  refinement_prompt?: string;
  generation_time?: number;
  timestamp: string;
  source_type?: 'asset_search' | 'ai_generation';
  asset_metadata?: AssetMetadata;
}
