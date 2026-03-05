export interface Doctor {
  id: string;
  name: string;
  email: string;
  specialty: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: string;
  doctor_id: string;
  filename: string;
  content: string;
  file_type: string;
  file_size: number;
  created_at: string;
}

export interface GroundingInfo {
  is_grounded: boolean;
  overall_confidence: number;
  section_scores: Record<string, number>;
  issues: string[];
  hallucinated_claims: string[];
}

export interface ReviewInfo {
  overall_quality: number;
  medical_accuracy: number;
  terminology_correctness: number;
  completeness: number;
  style_adherence: number;
  critical_issues: string[];
  suggestions: string[];
}

export interface AgentTraceEntry {
  agent: string;
  success: boolean;
  confidence: number;
  revision?: number;
  error?: string;
}

export interface Report {
  id: string;
  doctor_id: string;
  input_text: string;
  report_type: string;
  body_region: string;
  findings: string;
  impressions: string;
  recommendations: string;
  status: 'draft' | 'edited' | 'final';
  grounding?: GroundingInfo;
  review?: ReviewInfo;
  revisions: number;
  decision: string;
  pipeline_trace: AgentTraceEntry[];
  created_at: string;
  updated_at: string;
}

export interface StyleProfile {
  doctor_id: string;
  vocabulary_patterns: string[];
  abbreviation_map: Record<string, string>;
  sentence_structure: string[];
  section_ordering: string[];
  sample_phrases: string[];
  updated_at: string;
}

export interface GenerateRequest {
  doctor_id: string;
  dictated_text: string;
  report_type: string;
  body_region: string;
}

export interface GenerateResponse extends Report {}

export interface ReportVersion {
  version: number;
  findings: string;
  impressions: string;
  recommendations: string;
  status: string;
  edited_at: string;
}

export interface UsageStatsData {
  total_generations: number;
  avg_response_time_ms: number;
  reports_this_week: number;
  daily_usage: { date: string; count: number }[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface PipelineInfo {
  version: string;
  pipeline: string;
  agents: { name: string; role: string; pattern: string }[];
  orchestration_pattern: string;
  max_revisions: number;
  model: string;
  region: string;
}
