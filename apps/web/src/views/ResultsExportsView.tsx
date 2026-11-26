import React, { useMemo, useState } from "react";
import type { PlotlyTrace } from "plotly.js-basic-dist-min";
import {
  API_BASE,
  api,
  type AnalysisDetailResponse,
  type AnalysisSummaryItem,
  type BenchmarkEnvelope,
  type ExportBundleItem,
  type PublicationReadinessResponse,
} from "../api";
import type { UiMode } from "../App";
import { PlotlyChart } from "../components/PlotlyChart";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";

interface ResultsExportsViewProps {
  uiMode: UiMode;
  benchmarks: BenchmarkEnvelope[];
  analyses: AnalysisSummaryItem[];
  exportsList: ExportBundleItem[];
  publicationReadiness?: PublicationReadinessResponse | null;
  theme: "dark" | "light";
  onError: (msg: string | null) => void;
}

interface PreviewArtifactState {
  exportKey: string;
  relFile: string;
  kind: "image" | "text";
  textContent?: string;
}

export const ResultsExportsView: React.FC<ResultsExportsViewProps> = ({
  uiMode,
  benchmarks,
  analyses,
  exportsList,
  publicationReadiness = null,
  theme,
  onError,
}) => {
  const { t } = useI18n();
  const [analysisSearch, setAnalysisSearch] = useState<string>("");
  const [selectedAnalysisDetail, setSelectedAnalysisDetail] =
    useState<AnalysisDetailResponse | null>(null);
  const [previewArtifact, setPreviewArtifact] = useState<PreviewArtifactState | null>(null);

  const [compareKeyA, setCompareKeyA] = useState<string>("");
  const [compareKeyB, setCompareKeyB] = useState<string>("");

  const activeCompareA = useMemo(
    () => analyses.find((a) => a.analysis_key === compareKeyA) ?? analyses[0] ?? null,
    [analyses, compareKeyA],
  );
  const activeCompareB = useMemo(
    () =>
      analyses.find((a) => a.analysis_key === compareKeyB) ?? analyses[1] ?? analyses[0] ?? null,
    [analyses, compareKeyB],
  );

  const compareTraces = useMemo<PlotlyTrace[]>(() => {
    if (!activeCompareA || !activeCompareB || analyses.length < 2) return [];
    const items = [activeCompareA, activeCompareB];
    return [
      {
        type: "bar",
        name: t("meanDeltaLabel"),
        x: items.map((item) => item.analysis_key),
        y: items.map((item) => item.paired_metrics.mean_difference_hz),
        error_y: {
          type: "data",
          symmetric: false,
          array: items.map((item) =>
            Math.max(
              0,
              item.paired_metrics.bootstrap_ci95_high_hz - item.paired_metrics.mean_difference_hz,
            ),
          ),
          arrayminus: items.map((item) =>
            Math.max(
              0,
              item.paired_metrics.mean_difference_hz - item.paired_metrics.bootstrap_ci95_low_hz,
            ),
          ),
          visible: true,
        },
        marker: { color: ["#38bdf8", "#10b981"] },
      },
    ];
  }, [activeCompareA, activeCompareB, analyses.length, t]);

  const primaryBenchmark = benchmarks[0]?.report;
  const benchmarkTraces = useMemo<PlotlyTrace[]>(() => {
    if (!primaryBenchmark) return [];
    const comps = primaryBenchmark.target_comparisons;
    const labels = comps.map((c) => `${c.condition_id} (${c.label})`);
    return [
      {
        type: "bar",
        name: t("benchmarkSynthTrace"),
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
        name: t("benchmarkRefTrace"),
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
  }, [primaryBenchmark, t]);

  const filteredAnalyses = useMemo(() => {
    const q = analysisSearch.trim().toLowerCase();
    if (!q) return analyses;
    return analyses.filter(
      (a) =>
        a.analysis_key.toLowerCase().includes(q) ||
        a.target_neuron_id.toLowerCase().includes(q) ||
        a.provenance.protocol_id.toLowerCase().includes(q),
    );
  }, [analyses, analysisSearch]);

  const pairedDetailTraces = useMemo<PlotlyTrace[]>(() => {
    if (!selectedAnalysisDetail) return [];
    const pairs = selectedAnalysisDetail.paired_differences;
    return [
      {
        type: "bar",
        name: t("meanDeltaLabel"),
        x: pairs.map((p) => `rep ${p.replicate_id}`),
        y: pairs.map((p) => p.difference_hz),
        marker: {
          color: pairs.map((p) => (p.difference_hz >= 0 ? "#10b981" : "#f43f5e")),
        },
      },
    ];
  }, [selectedAnalysisDetail, t]);

  const handleLoadAnalysisDetail = async (analysisKey: string) => {
    onError(null);
    try {
      const detail = await api.analysisDetail(analysisKey);
      setSelectedAnalysisDetail(detail);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load paired distribution");
    }
  };

  const handlePreviewBundleFile = async (exportKey: string, relFile: string) => {
    onError(null);
    const lower = relFile.toLowerCase();
    if (lower.endsWith(".svg") || lower.endsWith(".png")) {
      setPreviewArtifact({ exportKey, relFile, kind: "image" });
      return;
    }
    try {
      const txt = await api.exportFileText(exportKey, relFile);
      setPreviewArtifact({ exportKey, relFile, kind: "text", textContent: txt });
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to preview artifact file");
    }
  };

  const isPreviewable = (relFile: string) => {
    const lower = relFile.toLowerCase();
    return (
      lower.endsWith(".svg") ||
      lower.endsWith(".png") ||
      lower.endsWith(".md") ||
      lower.endsWith(".json") ||
      lower.endsWith(".yaml")
    );
  };

  const analysesCard = (
    <div className="card">
      <div className="card-header">
        <h3>
          {t("analysesTitle")} ({filteredAnalyses.length})
        </h3>
        <input
          value={analysisSearch}
          onChange={(e) => setAnalysisSearch(e.target.value)}
          placeholder={t("searchAnalysesPlaceholder")}
        />
      </div>
      {filteredAnalyses.map((an) => (
        <div
          key={an.analysis_key}
          style={{
            marginBottom: 12,
            padding: 12,
            borderRadius: 9,
            background: "var(--bg-panel-subtle)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <div className="card-header" style={{ marginBottom: 6 }}>
            <strong className="mono">{an.analysis_key}</strong>
            <StatusBadge
              label={an.provenance.is_synthetic_fixture ? t("synthBadge") : t("bioRuoBadge")}
              tone={an.provenance.is_synthetic_fixture ? "synth" : "warn"}
            />
          </div>
          <p style={{ margin: "4px 0", fontSize: "0.82rem" }}>
            {t("targetNeuronLabel")}: <span className="mono">{an.target_neuron_id}</span> |{" "}
            {t("pairsLabel")}: <strong>{an.paired_metrics.n_pairs}</strong> |{" "}
            {t("meanDeltaLabel")}:{" "}
            <strong>{an.paired_metrics.mean_difference_hz.toFixed(3)} Hz</strong> (95% CI [
            {an.paired_metrics.bootstrap_ci95_low_hz.toFixed(3)},{" "}
            {an.paired_metrics.bootstrap_ci95_high_hz.toFixed(3)}] Hz)
          </p>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 8,
              marginTop: 6,
            }}
          >
            {an.paired_metrics.permutation_test && (
              <span className="mono" style={{ color: "var(--text-secondary)" }}>
                {t("permTestLabel")} ({an.paired_metrics.permutation_test.method}): p ={" "}
                {an.paired_metrics.permutation_test.two_sided_p_value.toExponential(3)}
              </span>
            )}
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void handleLoadAnalysisDetail(an.analysis_key)}
            >
              {t("inspectPairsBtn")}
            </button>
          </div>
        </div>
      ))}
    </div>
  );

  const exportsCard = (
    <div className="card">
      <div className="card-header">
        <h3>
          {t("exportsTitle")} ({exportsList.length})
        </h3>
      </div>
      {exportsList.length === 0 ? (
        <div className="empty-state">{t("noExportsMsg")}</div>
      ) : (
        exportsList.map((ex) => (
          <div
            key={ex.export_key}
            style={{
              marginBottom: 12,
              padding: 12,
              borderRadius: 9,
              background: "var(--bg-panel-subtle)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <p style={{ margin: "0 0 8px" }}>
              <strong className="mono">{ex.export_key}</strong>{" "}
              {ex.is_synthetic_fixture && <StatusBadge label={t("synthBadge")} tone="synth" />}
            </p>
            <ul
              style={{
                margin: 0,
                paddingLeft: 0,
                listStyle: "none",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              {ex.files.map((relFile) => (
                <li
                  key={relFile}
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 8,
                    fontSize: "0.79rem",
                  }}
                >
                  <span className="mono">{relFile}</span>
                  <span style={{ display: "inline-flex", gap: 6 }}>
                    {isPreviewable(relFile) && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => void handlePreviewBundleFile(ex.export_key, relFile)}
                      >
                        {t("previewBtn")}
                      </button>
                    )}
                    <a
                      className="btn btn-secondary btn-sm"
                      href={`${API_BASE}/api/v1/exports/${encodeURIComponent(ex.export_key)}/files/${relFile}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t("openRawBtn")}
                    </a>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  );

  return (
    <section role="tabpanel" aria-label={t("navResults")}>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">{t("qcZeroFailed")}</div>
          <div className="kpi-value">
            {primaryBenchmark ? primaryBenchmark.failed_run_count : t("noneDash")}
          </div>
          <div className="kpi-sub">
            {primaryBenchmark ? primaryBenchmark.benchmark_id : t("qcStripTitle")}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">{t("kpiRuns")}</div>
          <div className="kpi-value">{analyses.length}</div>
          <div className="kpi-sub">{t("analysesTitle")}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">{t("kpiExports")}</div>
          <div className="kpi-value">{exportsList.length}</div>
          <div className="kpi-sub">{t("exportsTitle")}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">{t("qcSpecimenIso")}</div>
          <div className="kpi-value" style={{ fontSize: "1.05rem" }}>
            <StatusBadge label={t("qcIsolated")} tone="ok" />
          </div>
          <div className="kpi-sub">FlyWire FAFB v630 · MaleCNS v1.0</div>
        </div>
      </div>

      {primaryBenchmark ? (
        <div className="card">
          <div className="card-header">
            <div>
              <h2>
                {primaryBenchmark.benchmark_id}{" "}
                <StatusBadge
                  label={primaryBenchmark.overall_passed ? t("statusPass") : t("statusFail")}
                  tone={primaryBenchmark.overall_passed ? "ok" : "synth"}
                />{" "}
                {primaryBenchmark.provenance.is_synthetic_fixture && (
                  <StatusBadge label={t("synthBadge")} tone="synth" />
                )}
              </h2>
              <p className="card-subtitle mono">
                Dataset: {primaryBenchmark.provenance.dataset_id} (
                {primaryBenchmark.provenance.dataset_release}) | Model:{" "}
                {primaryBenchmark.provenance.model_id} | Failed runs:{" "}
                {primaryBenchmark.failed_run_count}
              </p>
            </div>
          </div>

          <PlotlyChart
            theme={theme}
            ariaLabel={primaryBenchmark.benchmark_id}
            traces={benchmarkTraces}
            layout={{
              barmode: "group",
              height: 360,
              yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
              margin: { l: 60, r: 20, t: 30, b: 110 },
            }}
          />

          {uiMode === "expert" && (
            <div className="table-wrap" style={{ marginTop: 12 }}>
              <table>
                <thead>
                  <tr>
                    <th>{t("colConditionShort")}</th>
                    <th>{t("colNeuron")}</th>
                    <th>{t("colLabel")}</th>
                    <th>N</th>
                    <th>{t("colSynMeanSd")}</th>
                    <th>{t("colRefMeanSd")}</th>
                    <th>{t("colAbsDiff")}</th>
                    <th>{t("colGate")}</th>
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
                          label={row.passed ? t("statusPass") : t("statusFail")}
                          tone={row.passed ? "ok" : "synth"}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">{t("noBenchmarkMsg")}</div>
        </div>
      )}

      {selectedAnalysisDetail && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3>
                {t("pairedDistTitle")}:{" "}
                <span className="mono">{selectedAnalysisDetail.analysis_key}</span>
              </h3>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedAnalysisDetail(null)}
            >
              {t("close")}
            </button>
          </div>
          <PlotlyChart
            theme={theme}
            ariaLabel={t("pairedDistTitle")}
            traces={pairedDetailTraces}
            layout={{
              height: 300,
              yaxis: { title: t("chartYAxisDeltaHz") },
              margin: { l: 55, r: 20, t: 25, b: 60 },
            }}
          />
        </div>
      )}

      {previewArtifact && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3>
                {t("bundlePreviewTitle")}:{" "}
                <span className="mono">
                  {previewArtifact.exportKey}/{previewArtifact.relFile}
                </span>
              </h3>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setPreviewArtifact(null)}
            >
              {t("close")}
            </button>
          </div>
          <div className="artifact-preview-box">
            {previewArtifact.kind === "image" ? (
              <img
                src={`${API_BASE}/api/v1/exports/${encodeURIComponent(previewArtifact.exportKey)}/files/${previewArtifact.relFile}`}
                alt={previewArtifact.relFile}
              />
            ) : (
              <pre className="code-panel mono" style={{ marginTop: 0 }}>
                {previewArtifact.textContent ?? ""}
              </pre>
            )}
          </div>
        </div>
      )}

      {uiMode === "expert" && (
        <div className="card">
          <div className="card-header">
            <h3>{t("compareTitle")}</h3>
          </div>
          {analyses.length < 2 || !activeCompareA || !activeCompareB ? (
            <div className="empty-state">{t("compareNeedTwo")}</div>
          ) : (
            <>
              <div className="form-row">
                <label className="field" style={{ flex: "1 1 240px" }}>
                  {t("compareSelectA")}
                  <select
                    value={activeCompareA.analysis_key}
                    onChange={(e) => setCompareKeyA(e.target.value)}
                  >
                    {analyses.map((a) => (
                      <option key={a.analysis_key} value={a.analysis_key}>
                        {a.analysis_key}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field" style={{ flex: "1 1 240px" }}>
                  {t("compareSelectB")}
                  <select
                    value={activeCompareB.analysis_key}
                    onChange={(e) => setCompareKeyB(e.target.value)}
                  >
                    {analyses.map((a) => (
                      <option key={a.analysis_key} value={a.analysis_key}>
                        {a.analysis_key}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="grid-2">
                <PlotlyChart
                  theme={theme}
                  ariaLabel={t("compareTitle")}
                  traces={compareTraces}
                  layout={{
                    height: 290,
                    yaxis: { title: t("chartYAxisDeltaHz") },
                    margin: { l: 55, r: 20, t: 25, b: 85 },
                  }}
                />
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>{t("colContrast")}</th>
                        <th>{t("colNeuron")}</th>
                        <th>{t("pairsLabel")}</th>
                        <th>{t("colDelta")}</th>
                        <th>{t("colCi95")}</th>
                        <th>{t("colPval")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[activeCompareA, activeCompareB].map((item, idx) => (
                        <tr key={`${item.analysis_key}-${idx}`}>
                          <td className="mono">{item.analysis_key}</td>
                          <td className="mono">{item.target_neuron_id}</td>
                          <td>{item.paired_metrics.n_pairs}</td>
                          <td>
                            <strong>{item.paired_metrics.mean_difference_hz.toFixed(3)}</strong> ±{" "}
                            {item.paired_metrics.sd_difference_hz.toFixed(3)}
                          </td>
                          <td className="mono">
                            [{item.paired_metrics.bootstrap_ci95_low_hz.toFixed(3)},{" "}
                            {item.paired_metrics.bootstrap_ci95_high_hz.toFixed(3)}]
                          </td>
                          <td className="mono">
                            {item.paired_metrics.permutation_test
                              ? item.paired_metrics.permutation_test.two_sided_p_value.toExponential(
                                  3,
                                )
                              : t("noneDash")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {uiMode === "expert" ? (
        <div className="grid-2">
          {analysesCard}
          {exportsCard}
        </div>
      ) : (
        <>
          {exportsCard}
          <details className="tech-details">
            <summary>{t("showTechDetails")}</summary>
            {analysesCard}
          </details>
        </>
      )}

      {publicationReadiness && (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="card-header">
            <div>
              <h2>{t("pubReadinessTitle")}</h2>
              <p className="card-subtitle">{t("pubReadinessSubtitle")}</p>
            </div>
            <StatusBadge label={t("ruoBadge")} tone="ruo" />
          </div>

          <div className="kpi-grid" style={{ marginBottom: 12 }}>
            <div className="kpi-card">
              <div className="kpi-label">{t("pubBundlesKpi")}</div>
              <div className="kpi-value">
                {publicationReadiness.bundles.verified_passed} /{" "}
                {publicationReadiness.bundles.total_bundles}
              </div>
              <div className="kpi-sub">
                <StatusBadge
                  label={
                    publicationReadiness.bundles.verified_failed === 0
                      ? t("statusPass")
                      : t("statusFail")
                  }
                  tone={publicationReadiness.bundles.verified_failed === 0 ? "ok" : "warn"}
                />
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">{t("pubCitationsKpi")}</div>
              <div className="kpi-value">
                {publicationReadiness.citation_audit.peer_reviewed_count} +{" "}
                {publicationReadiness.citation_audit.preprint_count}
              </div>
              <div className="kpi-sub">
                {t("pubPreprintsNote")}:{" "}
                {publicationReadiness.citation_audit.preprint_ref_ids.join(", ") || t("noneDash")}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">{t("pubManuscriptsLabel")}</div>
              <div className="kpi-value">{publicationReadiness.manuscripts.length}</div>
              <div className="kpi-sub mono">
                {publicationReadiness.manuscripts.join(" · ") || t("noneDash")}
              </div>
            </div>
          </div>

          <div className="meta-strip" style={{ marginBottom: 10 }}>
            <span>
              <strong>{t("pubGovernanceLabel")}: </strong>
            </span>
            {Object.entries(publicationReadiness.governance_files).map(([fname, ok]) => (
              <StatusBadge
                key={fname}
                label={`${fname}: ${ok ? "OK" : "MISSING"}`}
                tone={ok ? "ok" : "warn"}
              />
            ))}
          </div>

          <div className="alert" role="note">
            <div>
              <strong>{t("pubHumanGatesLabel")}: </strong>
              <span>{publicationReadiness.human_approval_gates.join(" | ")}</span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
