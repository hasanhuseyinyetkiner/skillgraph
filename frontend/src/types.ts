export type Meta = {
  service: string;
  app_env: string;
  banner: string | null;
  embeddings_enabled: boolean;
  semantic_reason: string;
  method_version: string;
  weights_version: string;
  dataset_version?: string;
  weights: Record<string, number>;
  level_scale: Record<string, string>;
  component_definitions: Array<{
    key: string;
    credit: number | null;
    in_fit_index: boolean;
    summary: string;
  }>;
  fit_index_label: string;
  disclaimer: string;
  api_port: number;
};

export type ProfileSkill = {
  skill_id: number;
  canonical_name: string | null;
  category: string | null;
  aliases: string[];
  self_assessed_level: number | null;
  asserted_label: string | null;
};

export type Profile = {
  id: number;
  slug: string;
  display_name: string;
  summary: string;
  synthetic: boolean;
  consent_metadata: Record<string, unknown> | null;
  skills: ProfileSkill[];
};

export type Role = {
  id: number;
  title: string;
  family: string;
  summary: string;
  requirements?: Array<Record<string, unknown>>;
};

export type GraphPayload = {
  graph_version: number;
  nodes: Array<{
    id: string;
    entity_id: number;
    kind: string;
    label: string;
    category?: string;
    family?: string;
    [key: string]: unknown;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
    weight: number;
    [key: string]: unknown;
  }>;
  node_count: number;
  edge_count: number;
  categories: string[];
  families: string[];
  relation_types: string[];
};

export type ScoreComponent = {
  contribution?: number;
  value?: number | null;
  in_fit_index?: boolean;
  note?: string;
  reason?: string;
  identity_requirement_count?: number;
  related_requirement_count?: number;
};

export type Recommendation = {
  fit_index: number;
  fit_index_label: string;
  disclaimer: string;
  coverage: number;
  method_version: string;
  weights_version: string;
  weights: Record<string, number>;
  components: Record<string, ScoreComponent>;
  mandatory_satisfied: boolean;
  mandatory_total: number;
  mandatory_satisfied_count: number;
  mandatory_gates?: {
    all_satisfied: boolean;
    total: number;
    satisfied_count: number;
    missing_count: number;
    statuses?: Record<string, number>;
  };
  missing_mandatories?: Array<{
    skill_id: number;
    skill_name: string;
    mandatory_status: string;
    match_type: string;
  }>;
  requirements: Array<{
    skill_id: number;
    skill_name: string;
    category: string;
    mandatory: boolean;
    match_type: string;
    mandatory_status: string;
    credit: number;
    [key: string]: unknown;
  }>;
  role: { id: number; title: string; family: string; summary: string };
  match_type_counts: Record<string, number>;
  trace_id: number;
  graph_version: number;
  profile_id: number;
  semantic?: { available: boolean; reason: string };
};

export type ProfileSummary = {
  profile: Profile;
  skill_count: number;
  fit_index_label: string;
  disclaimer: string;
  ontology: {
    skill_count: number;
    role_count: number;
    resource_count: number;
    graph_version: number;
  };
  role_fits: Array<{
    role_id: number;
    title: string;
    family: string;
    fit_index: number;
    mandatory_satisfied: boolean;
    mandatory_total: number;
    mandatory_gap_count: number;
  }>;
};

export type LearningPath = {
  graph_version: number;
  method_version: string;
  weights_version: string;
  profile_id: number;
  role: { id: number; title: string; family: string; summary: string };
  fit_index: number;
  fit_index_label: string;
  disclaimer: string;
  mandatory_satisfied: boolean;
  timeline: Array<Record<string, unknown>>;
  ordered_steps: Array<{
    skill_id: number;
    skill_name?: string;
    reason?: string;
    resources?: Array<Record<string, unknown>>;
    [key: string]: unknown;
  }>;
  cycle_blocks: unknown[];
  cycle_free: boolean;
  message: string;
  duration_hours_supplied_sum: number;
  resources_missing_duration: number;
  duration_note: string;
  trace_id: number;
};
