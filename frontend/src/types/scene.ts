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
  | 'queued'
  | 'analyzing'
  | 'generating'
  | 'processing'
  | 'completed'
  | 'failed';

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  stage_message?: string;
  scene_spec?: SceneSpec;
  model_url?: string;
  generation_time?: number;
  error?: string;
  created_at?: string;
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
}
