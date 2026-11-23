/** Typed /api/v1 client keeping all 64-bit biological neuron identifiers strictly as strings. */

export const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export interface HealthResponse {
  status: string;
  api_version: string;
  ruo_notice: string;
  bind_host: string;
  storage?: {
    data_dir_exists: boolean;
    runs_dir_exists: boolean;
    disk_free_gb: number | null;
    disk_total_gb: number | null;
  };
}

export interface DatasetSummary {
  dataset_id: string;
  release: string;
  species: string;
  sex: string;
  specimen_id: string;
  is_synthetic_fixture: boolean;
  on_disk: boolean;
  quality_report?: Record<string, unknown>;
  known_limitations?: string[];
}

export interface DatasetInspectResponse {
  dataset_id: string;
  release: string;
  specimen_id: string;
  is_synthetic_fixture: boolean;
  n_neurons: number;
  n_edges: number;
  total_synapses: number;
  graph_sha256: string;
  orientation: string;
  quality_report?: Record<string, unknown>;
  known_limitations?: string[];
}

export interface NeuronRow {
  source_neuron_id: string;
  cell_type?: string | null;
  region?: string | null;
  neurotransmitter?: string | null;
  confidence?: number | null;
}

export interface SubgraphResponse {
  metadata: {
    source_dataset_id: string;
    source_graph_sha256: string;
    subgraph_sha256: string;
    seed_neuron_ids: string[];
    hop_limit: number;
    direction: string;
    n_selected_neurons: number;
    n_selected_edges: number;
    omitted_incoming_edge_count: number;
    omitted_outgoing_edge_count: number;
    omitted_incoming_synapse_count: number;
    omitted_outgoing_synapse_count: number;
    isolation_limitations: string[];
  };
  nodes: Array<{
    source_neuron_id: string;
    neurotransmitter: string | null;
    is_seed: boolean;
    cell_type?: string | null;
    region?: string | null;
    soma_side?: string | null;
    superclass?: string | null;
  }>;
  edges: Array<{
    pre_neuron_id: string;
    post_neuron_id: string;
    synapse_count: number;
  }>;
  edges_truncated: boolean;
}

export interface DatasetPlanResponse {
  dataset_id: string;
  release: string;
  species: string;
  license: string;
  attribution: string;
  is_synthetic_fixture: boolean;
  credentials_required: boolean;
  approval_required: boolean;
  total_estimated_bytes: number | null;
  files: Array<{
    role: string;
    filename: string;
    source_uri: string;
    expected_bytes?: number | null;
    [key: string]: unknown;
  }>;
  notes: string[];
}

export interface ModelSummary {
  model_id: string;
  model_revision: string;
  model_level?: "L1" | "L3";
  parameter_manifest_sha256: string;
  solver: string;
  dt_s: number;
  dg_unless_refractory?: boolean;
  parameter_source: string;
  parameters?: Record<string, number | string | boolean>;
}

export interface BackendSummary {
  backend_id: string;
  device: string;
  precision: string;
  supported_solvers: string[];
  verified: boolean;
  reproducibility_class: string;
}

export interface ProtocolSummary {
  relative_path: string;
  protocol_id?: string;
  revision?: number;
  status: string;
  analysis_intent?: string;
  protocol_sha256?: string;
  question?: string;
  error?: string;
}

export interface ProtocolContentResponse {
  relative_path: string;
  yaml_text: string;
  size_bytes: number;
  protocol_id?: string;
  revision?: number;
  status?: string;
  analysis_intent?: string;
  protocol_sha256?: string;
  question?: string;
  hypothesis?: string;
  conditions_count?: number;
  validation_error?: string | null;
}

export interface JobSummary {
  job_id: string;
  parent_job_id: string | null;
  idempotency_key: string | null;
  kind: string;
  status: string;
  attempt_number: number;
  worker_id: string | null;
  worker_pid: number | null;
  error_message: string | null;
  created_at_utc: string;
  result: Record<string, unknown> | null;
}

export interface RunSummary {
  run_id: string;
  status: string;
  complete_marker: boolean;
  protocol_id: string;
  protocol_revision: number;
  condition_id: string;
  replicate_id: number;
  dataset_id: string;
  model_id: string;
  is_synthetic_fixture: boolean;
  analysis_intent: string;
  wall_seconds: number | null;
  failure_reason: string | null;
}

export interface RunDetailResponse {
  run_id: string;
  relative_dir: string;
  complete_marker: boolean;
  manifest: Record<string, unknown>;
  metrics_preview: Array<{
    source_neuron_id: string;
    spike_count?: number;
    firing_rate_hz?: number;
    [key: string]: unknown;
  }>;
}

export interface BenchmarkTargetComparison {
  condition_id: string;
  neuron_id: string;
  label: string;
  n_replicates: number;
  observed_mean_hz: number;
  observed_sd_pop_hz: number;
  reference_mean_hz: number;
  reference_sd_pop_hz: number;
  abs_diff_from_ref_hz: number;
  tolerance_abs_hz: number;
  passed: boolean;
}

export interface BenchmarkEnvelope {
  relative_path: string;
  report: {
    benchmark_id: string;
    overall_passed: boolean;
    failed_run_count: number;
    provenance: {
      dataset_id: string;
      dataset_release: string;
      model_id: string;
      protocol_id: string;
      protocol_revision: number;
      protocol_sha256: string;
      is_synthetic_fixture: boolean;
    };
    target_comparisons: BenchmarkTargetComparison[];
    contrast_comparisons: Array<{
      contrast_id: string;
      neuron_id: string;
      n_pairs: number;
      observed_mean_diff_hz: number;
      observed_sd_diff_hz: number;
      reference_mean_diff_hz: number;
      expected_direction: string;
      passed: boolean;
    }>;
  };
}

export interface AnalysisSummaryItem {
  analysis_key: string;
  relative_dir: string;
  target_neuron_id: string;
  baseline_condition: string;
  treatment_condition: string;
  failed_run_count: number;
  provenance: {
    dataset_id: string;
    model_id: string;
    protocol_id: string;
    protocol_sha256: string;
    is_synthetic_fixture: boolean;
  };
  paired_metrics: {
    n_pairs: number;
    mean_difference_hz: number;
    sd_difference_hz: number;
    bootstrap_ci95_low_hz: number;
    bootstrap_ci95_high_hz: number;
    uncertainty_interpretation: string;
    permutation_test?: {
      method: string;
      two_sided_p_value: number;
    };
  };
}

export interface AnalysisDetailResponse {
  analysis_key: string;
  manifest: Record<string, unknown>;
  paired_differences: Array<{
    replicate_id: number;
    target_neuron_id: string;
    baseline_hz: number;
    treatment_hz: number;
    difference_hz: number;
  }>;
}

export interface ExportBundleItem {
  export_key: string;
  relative_dir: string;
  is_synthetic_fixture: boolean;
  files: string[];
}

export interface AuditEventItem {
  id: number;
  created_at_utc: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
}

export type ModuleUiState =
  | "planned"
  | "experimental"
  | "reproduced"
  | "validated_for_declared_endpoint";

export interface ResearchModuleItem {
  module_id: string;
  phase: string;
  ui_state: ModuleUiState;
  simulation_phase: string;
  dataset_id: string | null;
  protocol_id: string | null;
  available_on_disk: boolean;
}

export interface PainContrastRow {
  contrast_name: string;
  neuron_id: string;
  baseline_condition: string;
  treatment_condition: string;
  n_pairs: number;
  failed_run_count: number;
  baseline_summary: { mean_hz: number; sd_hz: number };
  treatment_summary: { mean_hz: number; sd_hz: number };
  mean_difference_hz: number;
  sd_difference_hz: number;
  bootstrap_ci95_low_hz: number;
  bootstrap_ci95_high_hz: number;
  permutation_p: number;
  bh_fdr_q?: number;
}

export interface PainConfirmatorySummary {
  total_runs: number;
  failed_run_count: number;
  sham_count: number;
  sham_max_spikes: number;
  wall_total_s: number;
  run_wall_min_s: number;
  run_wall_mean_s: number;
  run_wall_max_s: number;
  git_commits: string[];
  git_dirty_values: boolean[];
  primary_contrasts: PainContrastRow[];
  secondary_contrasts: PainContrastRow[];
}

export interface WindowMetricStat {
  n_seed_replicates: number;
  mean: number;
  sd: number;
}

export interface PainWindowedSummary {
  windows: {
    pre_window_s: [number, number];
    stim_window_s: [number, number];
    post_window_s: [number, number];
  };
  neuron_ids: string[];
  succeeded_run_count: number;
  failed_run_count: number;
  per_neuron_condition_summaries: Record<
    string,
    Record<
      string,
      {
        pre_rate_hz: WindowMetricStat;
        stim_rate_hz: WindowMetricStat;
        post_rate_hz: WindowMetricStat;
        persistence_duration_s: WindowMetricStat;
      }
    >
  >;
}

export interface PainRobustnessArmNeuron {
  baseline_mean_hz: number;
  baseline_sd_hz: number;
  treatment_mean_hz: number;
  treatment_sd_hz: number;
  mean_difference_hz: number;
  sd_difference_hz: number;
  ci95_low_hz: number;
  ci95_high_hz: number;
  p_value: number;
  method: string;
}

export interface PainRobustnessSummary {
  total_runs: number;
  failed_run_count: number;
  total_wall_seconds: number;
  arms: Record<
    string,
    {
      protocol_id: string;
      protocol_sha256: string;
      model_id: string;
      w_syn_v: number;
      n_runs: number;
      failed_run_count: number;
      arm_wall_seconds: number;
      neurons: Record<string, PainRobustnessArmNeuron>;
    }
  >;
}

export interface MetabolicConfirmatoryAnalysis {
  analysis_key: string;
  target_neuron_id: string;
  baseline_condition: string;
  treatment_condition: string;
  failed_run_count: number;
  condition_summaries: Record<string, { mean_hz: number; sd_hz: number; n_seed_replicates: number }>;
  paired_metrics: AnalysisSummaryItem["paired_metrics"];
  provenance: Record<string, unknown>;
}

export interface SleepL3PrcPoint {
  ct_hours: number;
  pulse_start_h: number;
  pulse_end_h: number;
  phase_shift_h: number | null;
  direction: string;
}

export interface SleepL3GateReport {
  model_id: string;
  model_level: string;
  parameter_manifest_sha256: string;
  overall_passed: boolean;
  gates: {
    dd_free_running_and_convergence: {
      passed: boolean;
      tau_dd_coarse_h: number | null;
      tau_dd_sd_h: number | null;
      tau_dd_fine_h: number | null;
      convergence_abs_diff_h: number | null;
    };
    ld12_12_entrainment: {
      passed: boolean;
      tau_ld_h: number | null;
      zt_peak_mean_h: number | null;
      zt_peak_sd_h: number | null;
    };
    light_pulse_prc: {
      passed: boolean;
      max_abs_daytime_dead_zone_h: number | null;
      max_early_night_delay_h: number | null;
      late_night_ct21_advance_h: number | null;
      curve: SleepL3PrcPoint[];
    };
    homeostatic_deprivation_rebound: {
      passed: boolean;
      baseline_s_peak: number;
      deprivation_s_peak: number;
      baseline_24h_recovery_rest_fraction: number;
      deprivation_24h_recovery_rest_fraction: number;
      recovery_rest_fraction_delta: number;
      day9_washout_rest_fraction_delta: number;
    };
  };
}

export interface SleepL3ShiftArm {
  arm_id: string;
  duration_h: number;
  s_peak_overall: number;
  s_mean_post_onset: number;
  modeled_rest_fraction_post_onset: number;
  max_abs_phase_error_h: number;
  days_to_reentrain: number | null;
}

export interface SleepL3ShiftWorkSummary {
  model_id: string;
  parameter_manifest_sha256: string;
  gate_overall_passed: boolean;
  arms: Record<string, SleepL3ShiftArm>;
}

export interface SleepPilotContrast {
  contrast_name: string;
  neuron_id: string;
  baseline_condition: string;
  treatment_condition: string;
  n_pairs: number;
  failed_run_count: number;
  baseline_mean_hz: number;
  baseline_sd_hz: number;
  treatment_mean_hz: number;
  treatment_sd_hz: number;
  mean_difference_hz: number;
  sd_difference_hz: number;
  bootstrap_ci95_low_hz: number;
  bootstrap_ci95_high_hz: number;
}

export interface SleepPilotSummary {
  protocol_id: string;
  dataset_id: string;
  total_runs: number;
  succeeded_run_count: number;
  failed_run_count: number;
  sham_count: number;
  sham_max_spikes: number;
  wall_total_s: number;
  run_wall_mean_s: number;
  git_commits: string[];
  cohort_stim_mean_hz: Record<string, Record<string, number>>;
  contrasts: SleepPilotContrast[];
}

export interface SleepStudyData {
  l3_gate: SleepL3GateReport | null;
  l3_shift_work: SleepL3ShiftWorkSummary | null;
  pilot: SleepPilotSummary | null;
}

export interface StudiesResponse {
  modules: ResearchModuleItem[];
  metabolic: {
    confirmatory: MetabolicConfirmatoryAnalysis[];
    robustness: Record<
      string,
      {
        target_neuron_id: string;
        baseline_condition: string;
        treatment_condition: string;
        condition_summaries: Record<string, { mean_hz: number; sd_hz: number }>;
        paired_metrics: AnalysisSummaryItem["paired_metrics"];
        provenance: Record<string, unknown>;
      }
    >;
  };
  pain: {
    confirmatory: PainConfirmatorySummary | null;
    windowed: PainWindowedSummary | null;
    robustness: PainRobustnessSummary | null;
  };
  sleep?: SleepStudyData;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = await res.json();
  if (!res.ok) {
    const msg = body?.error?.message ?? `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return body as T;
}

export const api = {
  health: () => requestJson<HealthResponse>("/api/v1/health"),
  studies: () => requestJson<StudiesResponse>("/api/v1/studies"),
  datasets: () => requestJson<{ datasets: DatasetSummary[] }>("/api/v1/datasets"),
  datasetPlan: (datasetId: string) =>
    requestJson<DatasetPlanResponse>(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/plan`,
    ),
  datasetInspect: (datasetId: string) =>
    requestJson<DatasetInspectResponse>(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/inspect`,
    ),
  neurons: (datasetId: string, search = "", offset = 0, limit = 25) =>
    requestJson<{
      total: number;
      offset: number;
      limit: number;
      is_synthetic_fixture: boolean;
      neurons: NeuronRow[];
    }>(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/neurons?limit=${limit}&offset=${offset}&search=${encodeURIComponent(search)}`,
    ),
  subgraph: (
    datasetId: string,
    payload: {
      seed_neuron_ids: string[];
      hops: number;
      direction: string;
      min_synapses: number;
      max_nodes: number;
    },
  ) =>
    requestJson<SubgraphResponse>(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/subgraph`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  models: () =>
    requestJson<{ models: ModelSummary[]; backends: BackendSummary[] }>("/api/v1/models"),
  protocols: () =>
    requestJson<{ protocols: ProtocolSummary[] }>("/api/v1/protocols"),
  protocolContent: (protocolPath: string) =>
    requestJson<ProtocolContentResponse>(
      `/api/v1/protocols/content?protocol_path=${encodeURIComponent(protocolPath)}`,
    ),
  validateProtocol: (protocolPath: string, allowUnresolved: boolean) =>
    requestJson<Record<string, unknown>>("/api/v1/protocols/validate", {
      method: "POST",
      body: JSON.stringify({ protocol_path: protocolPath, allow_unresolved: allowUnresolved }),
    }),
  validateProtocolYaml: (yamlText: string, allowUnresolved: boolean) =>
    requestJson<Record<string, unknown>>("/api/v1/protocols/validate", {
      method: "POST",
      body: JSON.stringify({ yaml_text: yamlText, allow_unresolved: allowUnresolved }),
    }),
  freezeProtocol: (protocolPath: string, confirmed: boolean) =>
    requestJson<Record<string, unknown>>("/api/v1/protocols/freeze", {
      method: "POST",
      body: JSON.stringify({ protocol_path: protocolPath, confirmed }),
    }),
  planExperiment: (protocolPath: string, datasetId: string, replicates: number) =>
    requestJson<Record<string, unknown>>("/api/v1/experiments/plan", {
      method: "POST",
      body: JSON.stringify({
        protocol_path: protocolPath,
        dataset_id: datasetId,
        replicates,
      }),
    }),
  submitJob: (payload: Record<string, unknown>) =>
    requestJson<{ created: boolean; job: JobSummary }>("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  jobs: () => requestJson<{ jobs: JobSummary[] }>("/api/v1/jobs"),
  cancelJob: (jobId: string) =>
    requestJson<{ job: JobSummary }>(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: "POST",
    }),
  retryJob: (jobId: string) =>
    requestJson<{ job: JobSummary }>(`/api/v1/jobs/${encodeURIComponent(jobId)}/retry`, {
      method: "POST",
    }),
  runs: (params?: { limit?: number; offset?: number; protocolId?: string; status?: string }) => {
    const q = new URLSearchParams();
    q.set("limit", String(params?.limit ?? 50));
    if (params?.offset) q.set("offset", String(params.offset));
    if (params?.protocolId) q.set("protocol_id", params.protocolId);
    if (params?.status) q.set("status", params.status);
    return requestJson<{ total: number; runs: RunSummary[] }>(`/api/v1/runs?${q.toString()}`);
  },
  runDetail: (runId: string) =>
    requestJson<RunDetailResponse>(`/api/v1/runs/${encodeURIComponent(runId)}`),
  benchmarks: () =>
    requestJson<{ benchmarks: BenchmarkEnvelope[] }>("/api/v1/benchmarks"),
  analyses: () =>
    requestJson<{ analyses: AnalysisSummaryItem[] }>("/api/v1/analyses"),
  analysisDetail: (analysisKey: string) =>
    requestJson<AnalysisDetailResponse>(
      `/api/v1/analyses/${encodeURIComponent(analysisKey)}`,
    ),
  exports: () =>
    requestJson<{ exports: ExportBundleItem[] }>("/api/v1/exports"),
  exportFileText: async (exportKey: string, relPath: string): Promise<string> => {
    const res = await fetch(
      `${API_BASE}/api/v1/exports/${encodeURIComponent(exportKey)}/files/${relPath}`,
    );
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.text();
  },
  audit: () =>
    requestJson<{ events: AuditEventItem[] }>("/api/v1/audit?limit=30"),
};
