/** Typed /api/v1 client keeping all 64-bit biological neuron identifiers strictly as strings. */

export const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export interface HealthResponse {
  status: string;
  api_version: string;
  ruo_notice: string;
  bind_host: string;
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
  }>;
  edges: Array<{
    pre_neuron_id: string;
    post_neuron_id: string;
    synapse_count: number;
  }>;
  edges_truncated: boolean;
}

export interface ModelSummary {
  model_id: string;
  model_revision: string;
  parameter_manifest_sha256: string;
  solver: string;
  dt_s: number;
  dg_unless_refractory: boolean;
  parameter_source: string;
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
  datasets: () => requestJson<{ datasets: DatasetSummary[] }>("/api/v1/datasets"),
  neurons: (datasetId: string, search = "") =>
    requestJson<{ total: number; is_synthetic_fixture: boolean; neurons: NeuronRow[] }>(
      `/api/v1/datasets/${encodeURIComponent(datasetId)}/neurons?limit=25&offset=0&search=${encodeURIComponent(search)}`,
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
  validateProtocol: (protocolPath: string, allowUnresolved: boolean) =>
    requestJson<Record<string, unknown>>("/api/v1/protocols/validate", {
      method: "POST",
      body: JSON.stringify({ protocol_path: protocolPath, allow_unresolved: allowUnresolved }),
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
  runs: () => requestJson<{ total: number; runs: RunSummary[] }>("/api/v1/runs?limit=50"),
  benchmarks: () =>
    requestJson<{ benchmarks: BenchmarkEnvelope[] }>("/api/v1/benchmarks"),
  analyses: () =>
    requestJson<{ analyses: AnalysisSummaryItem[] }>("/api/v1/analyses"),
  exports: () =>
    requestJson<{ exports: ExportBundleItem[] }>("/api/v1/exports"),
  audit: () =>
    requestJson<{ events: AuditEventItem[] }>("/api/v1/audit?limit=30"),
};
