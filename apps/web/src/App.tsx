import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  API_BASE,
  api,
  type AnalysisSummaryItem,
  type AuditEventItem,
  type BackendSummary,
  type BenchmarkEnvelope,
  type DatasetSummary,
  type ExportBundleItem,
  type HealthResponse,
  type JobSummary,
  type ModelSummary,
  type NeuronRow,
  type ProtocolSummary,
  type RunSummary,
  type SubgraphResponse,
} from "./api";
import { PlotlyChart } from "./components/PlotlyChart";
import { StatusBadge } from "./components/StatusBadge";

type TabId = "overview" | "datasets" | "models" | "jobs" | "results";

const TABS: ReadonlyArray<{ id: TabId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "datasets", label: "Datasets & Circuits" },
  { id: "models", label: "Models & Protocols" },
  { id: "jobs", label: "Jobs & Runs" },
  { id: "results", label: "Results & Exports" },
];

export const App: React.FC = () => {
  const [tab, setTab] = useState<TabId>("overview");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [backends, setBackends] = useState<BackendSummary[]>([]);
  const [protocols, setProtocols] = useState<ProtocolSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkEnvelope[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisSummaryItem[]>([]);
  const [exportsList, setExportsList] = useState<ExportBundleItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);

  // Circuit explorer state (string IDs only)
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [neuronSearch, setNeuronSearch] = useState<string>("");
  const [neurons, setNeurons] = useState<NeuronRow[]>([]);
  const [neuronIsSynthetic, setNeuronIsSynthetic] = useState<boolean>(false);
  const [seedInput, setSeedInput] = useState<string>("720575940624963786");
  const [hops, setHops] = useState<number>(1);
  const [maxNodes, setMaxNodes] = useState<number>(100);
  const [subgraphResult, setSubgraphResult] = useState<SubgraphResponse | null>(null);

  // Protocol & freeze guard state
  const [selectedProtocol, setSelectedProtocol] = useState<string>("");
  const [protocolActionResult, setProtocolActionResult] = useState<string | null>(null);
  const [freezeConfirmed, setFreezeConfirmed] = useState<boolean>(false);

  // Job submission / dry-run state
  const [planResult, setPlanResult] = useState<string | null>(null);
  const [jobReplicates, setJobReplicates] = useState<number>(2);
  const [jobWorkName, setJobWorkName] = useState<string>("lab_run_01");

  const refreshAll = useCallback(async () => {
    setErrorMsg(null);
    try {
      const [h, ds, mod, proto, j, r, bm, an, ex, au] = await Promise.all([
        api.health(),
        api.datasets(),
        api.models(),
        api.protocols(),
        api.jobs(),
        api.runs(),
        api.benchmarks(),
        api.analyses(),
        api.exports(),
        api.audit(),
      ]);
      setHealth(h);
      setDatasets(ds.datasets);
      const firstOnDisk = ds.datasets.find((d) => d.on_disk);
      if (firstOnDisk) {
        setSelectedDataset((prev) => prev || firstOnDisk.dataset_id);
      }
      setModels(mod.models);
      setBackends(mod.backends);
      setProtocols(proto.protocols);
      const firstProto = proto.protocols.find((p) => p.relative_path);
      if (firstProto) {
        setSelectedProtocol((prev) => prev || firstProto.relative_path);
      }
      setJobs(j.jobs);
      setRuns(r.runs);
      setBenchmarks(bm.benchmarks);
      setAnalyses(an.analyses);
      setExportsList(ex.exports);
      setAuditEvents(au.events);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load API workspace");
    }
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const handleLoadNeurons = async (dsId: string, search = neuronSearch) => {
    if (!dsId) return;
    setErrorMsg(null);
    try {
      const res = await api.neurons(dsId, search);
      setNeurons(res.neurons);
      setNeuronIsSynthetic(res.is_synthetic_fixture);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to query neurons");
    }
  };

  const handleQuerySubgraph = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) return;
    setErrorMsg(null);
    const seedIds = seedInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const res = await api.subgraph(selectedDataset, {
        seed_neuron_ids: seedIds,
        hops,
        direction: "outgoing",
        min_synapses: 1,
        max_nodes: maxNodes,
      });
      setSubgraphResult(res);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Subgraph query failed");
    }
  };

  const handleValidateProtocol = async () => {
    if (!selectedProtocol) return;
    setErrorMsg(null);
    try {
      const res = await api.validateProtocol(selectedProtocol, false);
      setProtocolActionResult(JSON.stringify(res, null, 2));
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Protocol validation failed");
    }
  };

  const handleFreezeProtocol = async () => {
    if (!selectedProtocol || !freezeConfirmed) return;
    setErrorMsg(null);
    try {
      const res = await api.freezeProtocol(selectedProtocol, true);
      setProtocolActionResult(JSON.stringify(res, null, 2));
      setFreezeConfirmed(false);
      await refreshAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Protocol freeze failed");
    }
  };

  const handlePlanExperiment = async () => {
    if (!selectedProtocol || !selectedDataset) return;
    setErrorMsg(null);
    try {
      const res = await api.planExperiment(selectedProtocol, selectedDataset, jobReplicates);
      setPlanResult(JSON.stringify(res, null, 2));
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Dry-run plan failed");
    }
  };

  const handleSubmitJob = async () => {
    if (!selectedProtocol || !selectedDataset) return;
    setErrorMsg(null);
    try {
      await api.submitJob({
        kind: "protocol_experiment",
        protocol_path: selectedProtocol,
        dataset_id: selectedDataset,
        work_dir_name: jobWorkName,
        replicates: jobReplicates,
        workers: 1,
      });
      await refreshAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Job submission failed");
    }
  };

  const handleCancelJob = async (jobId: string) => {
    setErrorMsg(null);
    try {
      await api.cancelJob(jobId);
      await refreshAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to cancel job");
    }
  };

  const handleRetryJob = async (jobId: string) => {
    setErrorMsg(null);
    try {
      await api.retryJob(jobId);
      await refreshAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to retry job");
    }
  };

  const primaryBenchmark = benchmarks[0]?.report;
  const benchmarkTraces = useMemo(() => {
    if (!primaryBenchmark) return [];
    const comps = primaryBenchmark.target_comparisons;
    const labels = comps.map((c) => `${c.condition_id} (${c.label})`);
    return [
      {
        type: "bar",
        name: "SYNAPSE Mean ± 1 SD (Hz)",
        x: labels,
        y: comps.map((c) => c.observed_mean_hz),
        error_y: {
          type: "data",
          array: comps.map((c) => c.observed_sd_pop_hz),
          visible: true,
        },
        marker: { color: "#0072B2" },
      },
      {
        type: "bar",
        name: "Published Ref 91bdd1e ± 1 SD (Hz)",
        x: labels,
        y: comps.map((c) => c.reference_mean_hz),
        error_y: {
          type: "data",
          array: comps.map((c) => c.reference_sd_pop_hz),
          visible: true,
        },
        marker: { color: "#D55E00" },
      },
    ];
  }, [primaryBenchmark]);

  return (
    <div className="app-shell">
      <header className="ruo-banner">
        <div>
          <h1>SYNAPSE Computational Neuroscience Research Workbench</h1>
          <p>
            Local-first open science platform (Adult <em>Drosophila melanogaster</em> connectome
            modeling)
          </p>
        </div>
        <div>
          <StatusBadge label="RESEARCH USE ONLY (RUO)" tone="ruo" />
        </div>
      </header>

      <nav className="tablist" role="tablist" aria-label="SYNAPSE workspaces">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            className="tab-btn"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
        <button type="button" className="btn btn-secondary" onClick={() => void refreshAll()}>
          Refresh Workspace
        </button>
      </nav>

      {errorMsg && (
        <div className="alert" role="alert">
          {errorMsg}
        </div>
      )}

      {tab === "overview" && (
        <section role="tabpanel" aria-label="Overview">
          <div className="grid-2">
            <div className="card">
              <h2>System &amp; Verification Status</h2>
              <p>
                API status:{" "}
                <StatusBadge label={health ? health.status.toUpperCase() : "CONNECTING"} tone="ok" />
              </p>
              <p>
                Datasets registered: <strong>{datasets.length}</strong> | On-disk normalized:{" "}
                <strong>{datasets.filter((d) => d.on_disk).length}</strong>
              </p>
              <p>
                Discovered runs: <strong>{runs.length}</strong> | Benchmarks:{" "}
                <strong>{benchmarks.length}</strong> | Analyses: <strong>{analyses.length}</strong>
              </p>
              <p className="mono">Loopback host: {health?.bind_host ?? "127.0.0.1"}</p>
            </div>

            <div className="card">
              <h2>Scientific Scope Guardrails</h2>
              <ul>
                <li>Computational reproduction is NOT wet-lab biological validation.</li>
                <li>Synapse counts are linear model weights, not measured conductances.</li>
                <li>All synthetic fixtures remain tagged `SYNTHETIC FIXTURE`.</li>
                <li>Male MaleCNS and female FlyWire IDs are strictly isolated.</li>
              </ul>
            </div>
          </div>
        </section>
      )}

      {tab === "datasets" && (
        <section role="tabpanel" aria-label="Datasets and Circuits">
          <div className="card">
            <h2>Registered &amp; Normalized Datasets</h2>
            <table>
              <thead>
                <tr>
                  <th>Dataset ID</th>
                  <th>Release</th>
                  <th>Specimen / Sex</th>
                  <th>Status</th>
                  <th>Scope Tag</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds) => (
                  <tr key={ds.dataset_id}>
                    <td className="mono">{ds.dataset_id}</td>
                    <td>{ds.release}</td>
                    <td>
                      {ds.specimen_id} ({ds.sex})
                    </td>
                    <td>
                      <StatusBadge
                        label={ds.on_disk ? "NORMALIZED ON DISK" : "REGISTRY METADATA"}
                        tone={ds.on_disk ? "ok" : "neutral"}
                      />
                    </td>
                    <td>
                      <StatusBadge
                        label={ds.is_synthetic_fixture ? "SYNTHETIC FIXTURE" : "BIOLOGICAL RUO"}
                        tone={ds.is_synthetic_fixture ? "synth" : "warn"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid-2">
            <div className="card">
              <h3>Neuron ID Browser (64-bit String Preserved)</h3>
              <div className="form-row">
                <label className="field">
                  Dataset
                  <select
                    value={selectedDataset}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                  >
                    {datasets
                      .filter((d) => d.on_disk)
                      .map((d) => (
                        <option key={d.dataset_id} value={d.dataset_id}>
                          {d.dataset_id}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="field">
                  Search ID / Cell Type / Region
                  <input
                    value={neuronSearch}
                    onChange={(e) => setNeuronSearch(e.target.value)}
                    placeholder="e.g. MN9 or 7205..."
                  />
                </label>
                <button
                  type="button"
                  className="btn"
                  onClick={() => void handleLoadNeurons(selectedDataset)}
                >
                  Load Neurons
                </button>
              </div>
              {neuronIsSynthetic && (
                <p>
                  <StatusBadge label="SYNTHETIC FIXTURE — NOT BIOLOGICAL DATA" tone="synth" />
                </p>
              )}
              <table>
                <thead>
                  <tr>
                    <th>source_neuron_id (string)</th>
                    <th>Cell Type</th>
                    <th>NT</th>
                  </tr>
                </thead>
                <tbody>
                  {neurons.map((n) => (
                    <tr key={n.source_neuron_id}>
                      <td className="mono">{n.source_neuron_id}</td>
                      <td>{n.cell_type ?? "—"}</td>
                      <td>{n.neurotransmitter ?? "UNKNOWN"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3>Bounded Subgraph Extractor</h3>
              <form onSubmit={(e) => void handleQuerySubgraph(e)}>
                <div className="form-row">
                  <label className="field">
                    Seed Neuron IDs (comma-separated)
                    <input value={seedInput} onChange={(e) => setSeedInput(e.target.value)} />
                  </label>
                  <label className="field">
                    Hops
                    <input
                      type="number"
                      min={0}
                      max={4}
                      value={hops}
                      onChange={(e) => setHops(Number(e.target.value))}
                    />
                  </label>
                  <label className="field">
                    Max Nodes
                    <input
                      type="number"
                      min={1}
                      max={5000}
                      value={maxNodes}
                      onChange={(e) => setMaxNodes(Number(e.target.value))}
                    />
                  </label>
                  <button type="submit" className="btn">
                    Extract Subgraph
                  </button>
                </div>
              </form>
              {subgraphResult && (
                <div>
                  <p>
                    Nodes: <strong>{subgraphResult.metadata.n_selected_neurons}</strong> | Edges:{" "}
                    <strong>{subgraphResult.metadata.n_selected_edges}</strong> | Omitted incoming:{" "}
                    <strong>{subgraphResult.metadata.omitted_incoming_edge_count}</strong> |
                    Omitted outgoing:{" "}
                    <strong>{subgraphResult.metadata.omitted_outgoing_edge_count}</strong>
                  </p>
                  <p className="mono">
                    subgraph_sha256: {subgraphResult.metadata.subgraph_sha256}
                  </p>
                  <ul>
                    {subgraphResult.metadata.isolation_limitations.map((lim) => (
                      <li key={lim}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {tab === "models" && (
        <section role="tabpanel" aria-label="Models and Protocols">
          <div className="grid-2">
            <div className="card">
              <h2>LIF Models &amp; Backends</h2>
              <table>
                <thead>
                  <tr>
                    <th>Model ID</th>
                    <th>Solver</th>
                    <th>dt (s)</th>
                    <th>dg_unless_refractory</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.parameter_manifest_sha256}>
                      <td className="mono">{m.model_id}</td>
                      <td>{m.solver}</td>
                      <td>{m.dt_s}</td>
                      <td>{String(m.dg_unless_refractory)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <h3>Execution Backends</h3>
              <ul>
                {backends.map((b) => (
                  <li key={b.backend_id}>
                    <span className="mono">{b.backend_id}</span> ({b.device}):{" "}
                    <StatusBadge
                      label={b.verified ? "VERIFIED CPU REFERENCE" : "UNVERIFIED / LINUX OPT-IN"}
                      tone={b.verified ? "ok" : "warn"}
                    />
                  </li>
                ))}
              </ul>
            </div>

            <div className="card">
              <h2>Protocols &amp; Human Freeze Gate</h2>
              <div className="form-row">
                <label className="field">
                  Protocol File
                  <select
                    value={selectedProtocol}
                    onChange={(e) => setSelectedProtocol(e.target.value)}
                  >
                    {protocols.map((p) => (
                      <option key={p.relative_path} value={p.relative_path}>
                        {p.relative_path} ({p.status})
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => void handleValidateProtocol()}
                >
                  Validate
                </button>
              </div>
              <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
                <input
                  type="checkbox"
                  checked={freezeConfirmed}
                  onChange={(e) => setFreezeConfirmed(e.target.checked)}
                />
                <span>
                  I confirm freezing creates a new immutable protocol revision (`confirmed=true`).
                </span>
              </label>
              <button
                type="button"
                className="btn"
                disabled={!freezeConfirmed || !selectedProtocol}
                onClick={() => void handleFreezeProtocol()}
              >
                Freeze Protocol Revision
              </button>
              {protocolActionResult && <pre className="mono">{protocolActionResult}</pre>}
            </div>
          </div>
        </section>
      )}

      {tab === "jobs" && (
        <section role="tabpanel" aria-label="Jobs and Runs">
          <div className="card">
            <h2>Experiment Dry-Run &amp; Durable Job Submission</h2>
            <div className="form-row">
              <label className="field">
                Work Dir Name
                <input value={jobWorkName} onChange={(e) => setJobWorkName(e.target.value)} />
              </label>
              <label className="field">
                Replicates
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={jobReplicates}
                  onChange={(e) => setJobReplicates(Number(e.target.value))}
                />
              </label>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => void handlePlanExperiment()}
              >
                Dry-Run Plan
              </button>
              <button type="button" className="btn" onClick={() => void handleSubmitJob()}>
                Queue Job
              </button>
            </div>
            {planResult && <pre className="mono">{planResult}</pre>}
          </div>

          <div className="card">
            <h3>Durable Job Queue</h3>
            <table>
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Kind</th>
                  <th>Status</th>
                  <th>Attempt</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.job_id}>
                    <td className="mono">{j.job_id}</td>
                    <td>{j.kind}</td>
                    <td>
                      <StatusBadge
                        label={j.status.toUpperCase()}
                        tone={
                          j.status === "succeeded"
                            ? "ok"
                            : j.status === "failed" || j.status === "cancelled"
                              ? "synth"
                              : "warn"
                        }
                      />
                    </td>
                    <td>{j.attempt_number}</td>
                    <td>
                      {(j.status === "queued" ||
                        j.status === "preparing" ||
                        j.status === "running") && (
                        <button
                          type="button"
                          className="btn btn-danger"
                          onClick={() => void handleCancelJob(j.job_id)}
                        >
                          Cancel
                        </button>
                      )}
                      {(j.status === "failed" || j.status === "cancelled") && (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => void handleRetryJob(j.job_id)}
                        >
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Audit Events ({auditEvents.length})</h3>
            <table>
              <thead>
                <tr>
                  <th>UTC</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Resource</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.map((ev) => (
                  <tr key={ev.id}>
                    <td className="mono">{ev.created_at_utc}</td>
                    <td>{ev.actor}</td>
                    <td className="mono">{ev.action}</td>
                    <td className="mono">
                      {ev.resource_type}:{ev.resource_id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "results" && (
        <section role="tabpanel" aria-label="Results and Exports">
          {primaryBenchmark ? (
            <div className="card">
              <h2>
                {primaryBenchmark.benchmark_id}{" "}
                <StatusBadge
                  label={primaryBenchmark.overall_passed ? "PASS" : "FAIL"}
                  tone={primaryBenchmark.overall_passed ? "ok" : "synth"}
                />{" "}
                {primaryBenchmark.provenance.is_synthetic_fixture && (
                  <StatusBadge label="SYNTHETIC FIXTURE" tone="synth" />
                )}
              </h2>
              <p className="mono">
                Dataset: {primaryBenchmark.provenance.dataset_id} (
                {primaryBenchmark.provenance.dataset_release}) | Model:{" "}
                {primaryBenchmark.provenance.model_id} | Failed runs:{" "}
                {primaryBenchmark.failed_run_count}
              </p>
              <PlotlyChart
                ariaLabel="Benchmark firing rate comparison chart"
                traces={benchmarkTraces}
                layout={{
                  barmode: "group",
                  height: 360,
                  yaxis: { title: "Firing rate (Hz)", rangemode: "tozero" },
                  margin: { l: 60, r: 20, t: 30, b: 110 },
                }}
              />
              <table>
                <thead>
                  <tr>
                    <th>Condition</th>
                    <th>Neuron ID</th>
                    <th>Label</th>
                    <th>N</th>
                    <th>SYNAPSE Mean ± SD (Hz)</th>
                    <th>Ref Mean ± SD (Hz)</th>
                    <th>|Δ| (Hz)</th>
                    <th>Gate</th>
                  </tr>
                </thead>
                <tbody>
                  {primaryBenchmark.target_comparisons.map((row) => (
                    <tr key={`${row.condition_id}-${row.neuron_id}`}>
                      <td className="mono">{row.condition_id}</td>
                      <td className="mono">{row.neuron_id}</td>
                      <td>{row.label}</td>
                      <td>{row.n_replicates}</td>
                      <td>
                        {row.observed_mean_hz.toFixed(3)} ± {row.observed_sd_pop_hz.toFixed(3)}
                      </td>
                      <td>
                        {row.reference_mean_hz.toFixed(3)} ± {row.reference_sd_pop_hz.toFixed(3)}
                      </td>
                      <td>{row.abs_diff_from_ref_hz.toFixed(3)}</td>
                      <td>
                        <StatusBadge
                          label={row.passed ? "PASS" : "FAIL"}
                          tone={row.passed ? "ok" : "synth"}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="card">
              <p>No benchmark comparison reports found under local runs directory.</p>
            </div>
          )}

          <div className="grid-2">
            <div className="card">
              <h3>Paired Seed Ensemble Analyses</h3>
              {analyses.map((an) => (
                <div key={an.analysis_key} style={{ marginBottom: 12 }}>
                  <p>
                    <strong className="mono">{an.analysis_key}</strong>{" "}
                    <StatusBadge
                      label={
                        an.provenance.is_synthetic_fixture ? "SYNTHETIC FIXTURE" : "BIOLOGICAL RUO"
                      }
                      tone={an.provenance.is_synthetic_fixture ? "synth" : "warn"}
                    />
                  </p>
                  <p>
                    Target neuron: <span className="mono">{an.target_neuron_id}</span> | Pairs:{" "}
                    <strong>{an.paired_metrics.n_pairs}</strong> | Mean Δ:{" "}
                    <strong>{an.paired_metrics.mean_difference_hz.toFixed(3)} Hz</strong> (95%
                    bootstrap CI [{an.paired_metrics.bootstrap_ci95_low_hz.toFixed(3)},{" "}
                    {an.paired_metrics.bootstrap_ci95_high_hz.toFixed(3)}] Hz)
                  </p>
                  {an.paired_metrics.permutation_test && (
                    <p className="mono">
                      Permutation ({an.paired_metrics.permutation_test.method}): p ={" "}
                      {an.paired_metrics.permutation_test.two_sided_p_value.toExponential(3)}
                    </p>
                  )}
                </div>
              ))}
            </div>

            <div className="card">
              <h3>Publication Evidence Bundles</h3>
              {exportsList.map((ex) => (
                <div key={ex.export_key} style={{ marginBottom: 10 }}>
                  <p>
                    <strong className="mono">{ex.export_key}</strong>{" "}
                    {ex.is_synthetic_fixture && (
                      <StatusBadge label="SYNTHETIC FIXTURE" tone="synth" />
                    )}
                  </p>
                  <ul>
                    {ex.files.map((relFile) => (
                      <li key={relFile}>
                        <a
                          href={`${API_BASE}/api/v1/exports/${encodeURIComponent(ex.export_key)}/files/${relFile}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {relFile}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
