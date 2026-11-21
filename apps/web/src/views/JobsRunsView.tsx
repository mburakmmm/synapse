import React, { useEffect, useMemo, useState } from "react";
import {
  api,
  type AuditEventItem,
  type JobSummary,
  type RunDetailResponse,
  type RunSummary,
} from "../api";
import { StatusBadge, type BadgeTone } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";

interface JobsRunsViewProps {
  selectedProtocol: string;
  selectedDataset: string;
  jobs: JobSummary[];
  runs: RunSummary[];
  runsTotal: number;
  auditEvents: AuditEventItem[];
  onRefresh: () => Promise<void>;
  onError: (msg: string | null) => void;
}

function jobTone(status: string): BadgeTone {
  if (status === "succeeded") return "ok";
  if (status === "failed" || status === "cancelled") return "synth";
  return "warn";
}

export const JobsRunsView: React.FC<JobsRunsViewProps> = ({
  selectedProtocol,
  selectedDataset,
  jobs,
  runs: initialRuns,
  runsTotal: initialRunsTotal,
  auditEvents,
  onRefresh,
  onError,
}) => {
  const { t } = useI18n();
  const [jobWorkName, setJobWorkName] = useState<string>("lab_run_01");
  const [jobReplicates, setJobReplicates] = useState<number>(2);
  const [planResult, setPlanResult] = useState<string | null>(null);
  const [jobFilter, setJobFilter] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);

  const [protocolFilter, setProtocolFilter] = useState<string>("");
  const [runsOffset, setRunsOffset] = useState<number>(0);
  const [filteredRuns, setFilteredRuns] = useState<RunSummary[] | null>(null);
  const [filteredTotal, setFilteredTotal] = useState<number>(0);
  const [runDetail, setRunDetail] = useState<RunDetailResponse | null>(null);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(() => {
      void onRefresh();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, onRefresh]);

  const visibleJobs = useMemo(
    () => (jobFilter === "all" ? jobs : jobs.filter((j) => j.status === jobFilter)),
    [jobs, jobFilter],
  );

  const displayedRuns = filteredRuns ?? initialRuns;
  const displayedTotal =
    filteredRuns !== null ? filteredTotal : initialRunsTotal || initialRuns.length;

  const translateStatus = (raw: string): string => {
    switch (raw) {
      case "succeeded":
        return t("statusSucceeded");
      case "failed":
        return t("statusFailed");
      case "cancelled":
        return t("statusCancelled");
      case "queued":
        return t("statusQueued");
      case "running":
        return t("statusRunning");
      case "preparing":
        return t("statusPreparing");
      case "cancel_requested":
        return t("statusCancelRequested");
      default:
        return raw.toUpperCase();
    }
  };

  const handlePlanExperiment = async () => {
    if (!selectedProtocol || !selectedDataset) return;
    onError(null);
    try {
      const res = await api.planExperiment(selectedProtocol, selectedDataset, jobReplicates);
      setPlanResult(JSON.stringify(res, null, 2));
    } catch (err) {
      onError(err instanceof Error ? err.message : "Dry-run plan failed");
    }
  };

  const handleSubmitJob = async () => {
    if (!selectedProtocol || !selectedDataset) return;
    onError(null);
    try {
      await api.submitJob({
        kind: "protocol_experiment",
        protocol_path: selectedProtocol,
        dataset_id: selectedDataset,
        work_dir_name: jobWorkName,
        replicates: jobReplicates,
        workers: 1,
      });
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Job submission failed");
    }
  };

  const handleCancelJob = async (jobId: string) => {
    onError(null);
    try {
      await api.cancelJob(jobId);
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to cancel job");
    }
  };

  const handleRetryJob = async (jobId: string) => {
    onError(null);
    try {
      await api.retryJob(jobId);
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to retry job");
    }
  };

  const fetchRunsPage = async (nextOffset: number) => {
    onError(null);
    try {
      const res = await api.runs({
        limit: 50,
        offset: nextOffset,
        protocolId: protocolFilter.trim() || undefined,
      });
      setRunsOffset(nextOffset);
      setFilteredRuns(res.runs);
      setFilteredTotal(res.total);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to filter runs");
    }
  };

  const handleFilterRuns = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetchRunsPage(0);
  };

  const handleInspectRun = async (runId: string) => {
    onError(null);
    try {
      const res = await api.runDetail(runId);
      setRunDetail(res);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load run details");
    }
  };

  return (
    <section role="tabpanel" aria-label={t("navJobs")}>
      <div className="card">
        <div className="card-header">
          <div>
            <h2>{t("jobPlannerTitle")}</h2>
            <p className="card-subtitle mono">
              protocol={selectedProtocol || t("noneDash")} · dataset={selectedDataset || t("noneDash")}
            </p>
          </div>
        </div>
        <div className="form-row">
          <label className="field">
            {t("workDirLabel")}
            <input value={jobWorkName} onChange={(e) => setJobWorkName(e.target.value)} />
          </label>
          <label className="field" style={{ width: 120 }}>
            {t("replicatesLabel")}
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
            {t("dryRunBtn")}
          </button>
          <button type="button" className="btn" onClick={() => void handleSubmitJob()}>
            {t("queueJobBtn")}
          </button>
        </div>
        {planResult && <pre className="code-panel mono">{planResult}</pre>}
      </div>

      <div className="card">
        <div className="card-header">
          <h3>
            {t("jobQueueTitle")} ({visibleJobs.length})
          </h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              className={`btn btn-sm ${autoRefresh ? "" : "btn-secondary"}`}
              onClick={() => setAutoRefresh((v) => !v)}
            >
              {t("autoRefreshLabel")}
            </button>
            <div className="segmented">
              {["all", "queued", "running", "succeeded", "failed", "cancelled"].map((st) => (
                <button
                  key={st}
                  type="button"
                  className="seg-btn"
                  aria-pressed={jobFilter === st}
                  onClick={() => setJobFilter(st)}
                >
                  {st === "all" ? t("filterAll") : translateStatus(st)}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("colJobId")}</th>
                <th>{t("colKind")}</th>
                <th>{t("colStatus")}</th>
                <th>{t("colAttempt")}</th>
                <th>{t("colAction")}</th>
              </tr>
            </thead>
            <tbody>
              {visibleJobs.map((j) => (
                <tr key={j.job_id}>
                  <td className="mono">{j.job_id}</td>
                  <td className="mono">{j.kind}</td>
                  <td>
                    <StatusBadge label={translateStatus(j.status)} tone={jobTone(j.status)} />
                  </td>
                  <td>{j.attempt_number}</td>
                  <td>
                    {(j.status === "queued" ||
                      j.status === "preparing" ||
                      j.status === "running") && (
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        onClick={() => void handleCancelJob(j.job_id)}
                      >
                        {t("cancelBtn")}
                      </button>
                    )}
                    {(j.status === "failed" || j.status === "cancelled") && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => void handleRetryJob(j.job_id)}
                      >
                        {t("retryBtn")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3>
              {t("runsExplorerTitle")} ({displayedTotal})
            </h3>
          </div>
          <form
            onSubmit={(e) => void handleFilterRuns(e)}
            style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}
          >
            <input
              value={protocolFilter}
              onChange={(e) => setProtocolFilter(e.target.value)}
              placeholder={t("filterProtocolLabel")}
            />
            <button type="submit" className="btn btn-secondary btn-sm">
              {t("applyFilterBtn")}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={runsOffset === 0}
              onClick={() => void fetchRunsPage(Math.max(0, runsOffset - 50))}
            >
              {t("prev50")}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={runsOffset + displayedRuns.length >= displayedTotal}
              onClick={() => void fetchRunsPage(runsOffset + 50)}
            >
              {t("next50")}
            </button>
          </form>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("colRunId")}</th>
                <th>{t("colProtocol")}</th>
                <th>{t("colCondition")}</th>
                <th>{t("colRep")}</th>
                <th>{t("colWall")}</th>
                <th>{t("colStatus")}</th>
                <th>{t("colAction")}</th>
              </tr>
            </thead>
            <tbody>
              {displayedRuns.map((r) => (
                <tr key={r.run_id}>
                  <td className="mono">{r.run_id}</td>
                  <td className="mono">{r.protocol_id}</td>
                  <td className="mono">{r.condition_id}</td>
                  <td>{r.replicate_id}</td>
                  <td className="mono">
                    {r.wall_seconds !== null ? r.wall_seconds.toFixed(2) : t("noneDash")}
                  </td>
                  <td>
                    <StatusBadge
                      label={translateStatus(r.status)}
                      tone={r.status === "succeeded" ? "ok" : "warn"}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => void handleInspectRun(r.run_id)}
                    >
                      {t("inspectRunBtn")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {runDetail && (
          <div className="card" style={{ marginTop: 14, marginBottom: 0 }}>
            <div className="card-header">
              <div>
                <h3>
                  {t("runDetailTitle")}: <span className="mono">{runDetail.run_id}</span>
                </h3>
                <p className="card-subtitle mono">
                  {runDetail.relative_dir} · COMPLETE={String(runDetail.complete_marker)}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setRunDetail(null)}
              >
                {t("close")}
              </button>
            </div>
            {runDetail.metrics_preview.length > 0 && (
              <div className="table-wrap" style={{ marginBottom: 10 }}>
                <table>
                  <thead>
                    <tr>
                      <th>{t("colNeuronId")}</th>
                      <th>spike_count</th>
                      <th>firing_rate_hz</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runDetail.metrics_preview.slice(0, 10).map((row) => (
                      <tr key={row.source_neuron_id}>
                        <td className="mono">{row.source_neuron_id}</td>
                        <td className="mono">{String(row.spike_count ?? t("noneDash"))}</td>
                        <td className="mono">
                          {typeof row.firing_rate_hz === "number"
                            ? row.firing_rate_hz.toFixed(3)
                            : t("noneDash")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <pre className="code-panel mono">{JSON.stringify(runDetail.manifest, null, 2)}</pre>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h3>
            {t("auditTitle")} ({auditEvents.length})
          </h3>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("colUtc")}</th>
                <th>{t("colActor")}</th>
                <th>{t("colAction")}</th>
                <th>{t("colResource")}</th>
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
      </div>
    </section>
  );
};
