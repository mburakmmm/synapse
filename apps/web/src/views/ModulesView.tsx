import React, { useMemo, useState } from "react";
import type { PlotlyTrace } from "plotly.js-basic-dist-min";
import type { BenchmarkEnvelope, StudiesResponse } from "../api";
import type { UiMode } from "../App";
import { PlotlyChart } from "../components/PlotlyChart";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";

import type { CircuitPresetRequest } from "./DatasetsView";

export type ModuleSectionTab = "pain" | "metabolic" | "benchmark" | "planned";

interface ModulesViewProps {
  uiMode: UiMode;
  studies: StudiesResponse | null;
  benchmarks: BenchmarkEnvelope[];
  theme: "dark" | "light";
  activeSubTab: ModuleSectionTab;
  onSelectSubTab: (tab: ModuleSectionTab) => void;
  onJumpToResults: () => void;
  onExploreCircuit3D: (preset: Omit<CircuitPresetRequest, "nonce">) => void;
}

const PAIN_CONDITIONS_ORDER = [
  "mesoln_20hz_baseline",
  "mesoln_20hz_gaba_cell_death",
  "mesoln_40hz_baseline",
  "mesoln_40hz_matched_ctrl_ablation",
  "mesoln_40hz_gaba_atten_50pct",
  "mesoln_40hz_gaba_cell_death",
  "mesoln_40hz_acute_edge_mask",
];

const PAIN_CONDITION_SHORT: Record<string, string> = {
  mesoln_20hz_baseline: "20Hz Base",
  mesoln_20hz_gaba_cell_death: "20Hz Death",
  mesoln_40hz_baseline: "40Hz Base",
  mesoln_40hz_matched_ctrl_ablation: "40Hz Ctrl Abl",
  mesoln_40hz_gaba_atten_50pct: "40Hz Atten 50%",
  mesoln_40hz_gaba_cell_death: "40Hz Cell Death",
  mesoln_40hz_acute_edge_mask: "40Hz Edge Mask",
};

const PAIN_READOUT_LABELS: Record<string, string> = {
  "523539": "523539 (ANXXX027_L)",
  "558778": "558778 (AN08B012_R)",
  "10592": "10592 (AN08B012_L)",
  "15070": "15070 (Ascending)",
  "804642": "804642 (TTMn_L)",
};

export const ModulesView: React.FC<ModulesViewProps> = ({
  uiMode,
  studies,
  benchmarks,
  theme,
  activeSubTab,
  onSelectSubTab,
  onJumpToResults,
  onExploreCircuit3D,
}) => {
  const { t } = useI18n();
  const [painWindowMode, setPainWindowMode] = useState<"stim" | "post">("stim");

  const painConf = studies?.pain.confirmatory ?? null;
  const painWin = studies?.pain.windowed ?? null;
  const painRob = studies?.pain.robustness ?? null;
  const metConf = studies?.metabolic.confirmatory ?? [];
  const metRob = studies?.metabolic.robustness ?? {};

  const painWindowTraces = useMemo<PlotlyTrace[]>(() => {
    if (!painWin) return [];
    const metricKey = painWindowMode === "stim" ? "stim_rate_hz" : "post_rate_hz";
    const xLabels = PAIN_CONDITIONS_ORDER.map((c) => PAIN_CONDITION_SHORT[c] ?? c);
    return ["523539", "558778", "10592", "804642"]
      .filter((nid) => painWin.per_neuron_condition_summaries[nid])
      .map((nid) => {
        const condMap = painWin.per_neuron_condition_summaries[nid] ?? {};
        return {
          type: "bar",
          name: PAIN_READOUT_LABELS[nid] ?? nid,
          x: xLabels,
          y: PAIN_CONDITIONS_ORDER.map((cid) => condMap[cid]?.[metricKey]?.mean ?? 0),
          error_y: {
            type: "data",
            array: PAIN_CONDITIONS_ORDER.map((cid) => condMap[cid]?.[metricKey]?.sd ?? 0),
            visible: true,
          },
        };
      });
  }, [painWin, painWindowMode]);

  const painContrastTraces = useMemo<PlotlyTrace[]>(() => {
    if (!painConf) return [];
    const selectedSecondary = painConf.secondary_contrasts.filter((c) =>
      [
        "s_523539_40hz_ctrl_vs_base",
        "s_558778_40hz_ctrl_vs_base",
        "s_10592_40hz_edge_mask_vs_base",
        "s_10592_40hz_cell_death_vs_base",
      ].includes(c.contrast_name),
    );
    const combined = [...painConf.primary_contrasts, ...selectedSecondary];
    return [
      {
        type: "bar",
        name: t("meanDeltaLabel"),
        x: combined.map((c) => `${c.neuron_id}: ${c.contrast_name.replace(/^[ps]_\d+_/, "")}`),
        y: combined.map((c) => c.mean_difference_hz),
        error_y: {
          type: "data",
          symmetric: false,
          array: combined.map((c) => Math.max(0, c.bootstrap_ci95_high_hz - c.mean_difference_hz)),
          arrayminus: combined.map((c) =>
            Math.max(0, c.mean_difference_hz - c.bootstrap_ci95_low_hz),
          ),
          visible: true,
        },
        marker: {
          color: combined.map((c) =>
            c.bh_fdr_q !== undefined
              ? "#38bdf8"
              : c.mean_difference_hz < 0
                ? "#f43f5e"
                : "#94a3b8",
          ),
        },
      },
    ];
  }, [painConf, t]);

  const painRobustTraces = useMemo<PlotlyTrace[]>(() => {
    if (!painRob) return [];
    const armOrder = ["shiu_lif", "wsyn_low", "wsyn_high"].filter((k) => painRob.arms[k]);
    return ["523539", "558778", "10592"].map((nid) => ({
      type: "bar",
      name: PAIN_READOUT_LABELS[nid] ?? nid,
      x: armOrder,
      y: armOrder.map((a) => painRob.arms[a]?.neurons[nid]?.mean_difference_hz ?? 0),
      error_y: {
        type: "data",
        symmetric: false,
        array: armOrder.map((a) => {
          const item = painRob.arms[a]?.neurons[nid];
          return item ? Math.max(0, item.ci95_high_hz - item.mean_difference_hz) : 0;
        }),
        arrayminus: armOrder.map((a) => {
          const item = painRob.arms[a]?.neurons[nid];
          return item ? Math.max(0, item.mean_difference_hz - item.ci95_low_hz) : 0;
        }),
        visible: true,
      },
    }));
  }, [painRob]);

  const metContrastTraces = useMemo<PlotlyTrace[]>(() => {
    if (metConf.length === 0) return [];
    return [
      {
        type: "bar",
        name: "MN9 Δ (Hz)",
        x: metConf.map((m) => `${m.analysis_key} (${m.target_neuron_id.slice(-6)})`),
        y: metConf.map((m) => m.paired_metrics.mean_difference_hz),
        error_y: {
          type: "data",
          symmetric: false,
          array: metConf.map((m) =>
            Math.max(0, m.paired_metrics.bootstrap_ci95_high_hz - m.paired_metrics.mean_difference_hz),
          ),
          arrayminus: metConf.map((m) =>
            Math.max(0, m.paired_metrics.mean_difference_hz - m.paired_metrics.bootstrap_ci95_low_hz),
          ),
          visible: true,
        },
        marker: {
          color: metConf.map((m) =>
            m.paired_metrics.mean_difference_hz === 0 ? "#94a3b8" : "#10b981",
          ),
        },
      },
    ];
  }, [metConf]);

  const metRobustTraces = useMemo<PlotlyTrace[]>(() => {
    const keys = Object.keys(metRob);
    if (keys.length === 0) return [];
    return [
      {
        type: "bar",
        name: "50 Hz Baseline (Hz)",
        x: keys,
        y: keys.map((k) => {
          const arm = metRob[k];
          return arm.condition_summaries[arm.baseline_condition]?.mean_hz ?? 0;
        }),
      },
      {
        type: "bar",
        name: "1.50x Paired Δ (Hz)",
        x: keys,
        y: keys.map((k) => metRob[k].paired_metrics.mean_difference_hz),
        error_y: {
          type: "data",
          symmetric: false,
          array: keys.map((k) =>
            Math.max(
              0,
              metRob[k].paired_metrics.bootstrap_ci95_high_hz -
                metRob[k].paired_metrics.mean_difference_hz,
            ),
          ),
          arrayminus: keys.map((k) =>
            Math.max(
              0,
              metRob[k].paired_metrics.mean_difference_hz -
                metRob[k].paired_metrics.bootstrap_ci95_low_hz,
            ),
          ),
          visible: true,
        },
      },
    ];
  }, [metRob]);

  const plannedModules = useMemo(
    () => (studies?.modules ?? []).filter((m) => m.ui_state === "planned"),
    [studies],
  );

  return (
    <section role="tabpanel" aria-label={t("navModules")}>
      <div className="pill-group" role="group" aria-label={t("modulesTitle")}>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "pain"}
          onClick={() => onSelectSubTab("pain")}
        >
          <span>{t("tabPain")}</span>
          <StatusBadge label={t("stateExperimental")} tone="info" />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "metabolic"}
          onClick={() => onSelectSubTab("metabolic")}
        >
          <span>{t("tabMetabolic")}</span>
          <StatusBadge label={t("stateExperimental")} tone="info" />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "benchmark"}
          onClick={() => onSelectSubTab("benchmark")}
        >
          <span>{t("tabBenchmark")}</span>
          <StatusBadge
            label={benchmarks[0]?.report.overall_passed ? t("stateReproduced") : t("statePlanned")}
            tone={benchmarks[0]?.report.overall_passed ? "ok" : "neutral"}
          />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "planned"}
          onClick={() => onSelectSubTab("planned")}
        >
          <span>{t("tabPlanned")}</span>
          <StatusBadge label={t("statePlanned")} tone="neutral" />
        </button>
      </div>

      {activeSubTab === "pain" && (
        <>
          {!painConf ? (
            <div className="card">
              <div className="empty-state">
                <strong>{t("modulesMissingTitle")}</strong>
                <p style={{ marginBottom: 0 }}>{t("modulesMissingBody")}</p>
              </div>
            </div>
          ) : (
            <>
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>{t("painBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      malecns_v1_0 · synapse_lif_v1 · git {painConf.git_commits[0]?.slice(0, 8)} ·
                      git_dirty={String(painConf.git_dirty_values[0])}
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <StatusBadge label={t("stateExperimental")} tone="info" />
                    <StatusBadge label={t("ruoBadge")} tone="ruo" />
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() =>
                        onExploreCircuit3D({
                          datasetId: "malecns_v1_0",
                          seedIds: "523539, 558778, 10592, 804642",
                          hops: 1,
                          direction: "incoming",
                          minSynapses: 8,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>
                <div className="kpi-grid">
                  <div className="kpi-card">
                    <div className="kpi-label">{t("painMetricRuns")}</div>
                    <div className="kpi-value">{painConf.total_runs} / 120</div>
                    <div className="kpi-sub">failed: {painConf.failed_run_count}</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-label">{t("painMetricWall")}</div>
                    <div className="kpi-value">{painConf.wall_total_s.toFixed(1)} s</div>
                    <div className="kpi-sub">mean {painConf.run_wall_mean_s.toFixed(1)} s / run</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-label">{t("painMetricSham")}</div>
                    <div className="kpi-value">{painConf.sham_max_spikes}</div>
                    <div className="kpi-sub">n = {painConf.sham_count} replicates</div>
                  </div>
                  <div className="kpi-card">
                    <div className="kpi-label">{t("painMetricFdr")}</div>
                    <div className="kpi-value">{painConf.primary_contrasts.length} / 6</div>
                    <div className="kpi-sub">q = 9.9990e-05</div>
                  </div>
                </div>
              </div>

              {painWin && (
                <div className="card">
                  <div className="card-header">
                    <div>
                      <h3>{t("painChartWindowTitle")}</h3>
                      <p className="card-subtitle">{t("painPostNote")}</p>
                    </div>
                    <div className="segmented">
                      <button
                        type="button"
                        className="seg-btn"
                        aria-pressed={painWindowMode === "stim"}
                        onClick={() => setPainWindowMode("stim")}
                      >
                        {t("filterWindowStim")}
                      </button>
                      <button
                        type="button"
                        className="seg-btn"
                        aria-pressed={painWindowMode === "post"}
                        onClick={() => setPainWindowMode("post")}
                      >
                        {t("filterWindowPost")}
                      </button>
                    </div>
                  </div>
                  <PlotlyChart
                    theme={theme}
                    ariaLabel={t("painChartWindowTitle")}
                    traces={painWindowTraces}
                    layout={{
                      barmode: "group",
                      height: 350,
                      yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                      xaxis: { tickangle: -18 },
                      margin: { l: 55, r: 20, t: 35, b: 85 },
                    }}
                  />
                </div>
              )}

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simplePainTitle")}: </strong>
                  {t("simplePainSummary")}
                </div>
              )}

              {uiMode === "expert" ? (
                <>
                  <div className="grid-2">
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("painChartDeltaTitle")}</h3>
                      </div>
                      <PlotlyChart
                        theme={theme}
                        ariaLabel={t("painChartDeltaTitle")}
                        traces={painContrastTraces}
                        layout={{
                          height: 340,
                          yaxis: { title: t("chartYAxisDeltaHz") },
                          xaxis: { tickangle: -25 },
                          margin: { l: 55, r: 20, t: 25, b: 115 },
                        }}
                      />
                    </div>

                    {painRob && (
                      <div className="card">
                        <div className="card-header">
                          <h3>{t("painChartRobustTitle")}</h3>
                        </div>
                        <PlotlyChart
                          theme={theme}
                          ariaLabel={t("painChartRobustTitle")}
                          traces={painRobustTraces}
                          layout={{
                            barmode: "group",
                            height: 340,
                            yaxis: { title: t("chartYAxisDeltaHz"), rangemode: "tozero" },
                            margin: { l: 55, r: 20, t: 25, b: 60 },
                          }}
                        />
                      </div>
                    )}
                  </div>

                  <div className="card">
                    <div className="card-header">
                      <h3>{t("painDissocTitle")}</h3>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>{t("colContrast")}</th>
                            <th>{t("colNeuron")}</th>
                            <th>{t("colBaseMean")}</th>
                            <th>{t("colTreatMean")}</th>
                            <th>{t("colDelta")}</th>
                            <th>{t("colCi95")}</th>
                            <th>{t("colPval")}</th>
                            <th>{t("colQval")}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[...painConf.primary_contrasts, ...painConf.secondary_contrasts].map(
                            (row) => (
                              <tr key={row.contrast_name}>
                                <td className="mono">{row.contrast_name}</td>
                                <td className="mono">{row.neuron_id}</td>
                                <td>
                                  {row.baseline_summary.mean_hz.toFixed(3)} ±{" "}
                                  {row.baseline_summary.sd_hz.toFixed(3)}
                                </td>
                                <td>
                                  {row.treatment_summary.mean_hz.toFixed(3)} ±{" "}
                                  {row.treatment_summary.sd_hz.toFixed(3)}
                                </td>
                                <td>
                                  <strong>
                                    {row.mean_difference_hz >= 0 ? "+" : ""}
                                    {row.mean_difference_hz.toFixed(3)}
                                  </strong>{" "}
                                  ± {row.sd_difference_hz.toFixed(3)}
                                </td>
                                <td className="mono">
                                  [{row.bootstrap_ci95_low_hz.toFixed(3)},{" "}
                                  {row.bootstrap_ci95_high_hz.toFixed(3)}]
                                </td>
                                <td className="mono">{row.permutation_p.toExponential(3)}</td>
                                <td className="mono">
                                  {row.bh_fdr_q !== undefined
                                    ? row.bh_fdr_q.toExponential(3)
                                    : t("noneDash")}
                                </td>
                              </tr>
                            ),
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              ) : (
                <details className="tech-details">
                  <summary>{t("showTechDetails")}</summary>
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("painChartDeltaTitle")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("painChartDeltaTitle")}
                      traces={painContrastTraces}
                      layout={{
                        height: 320,
                        yaxis: { title: t("chartYAxisDeltaHz") },
                        xaxis: { tickangle: -25 },
                        margin: { l: 55, r: 20, t: 25, b: 115 },
                      }}
                    />
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{t("colContrast")}</th>
                          <th>{t("colNeuron")}</th>
                          <th>{t("colDelta")}</th>
                          <th>{t("colQval")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {painConf.primary_contrasts.map((row) => (
                          <tr key={row.contrast_name}>
                            <td className="mono">{row.contrast_name}</td>
                            <td className="mono">{row.neuron_id}</td>
                            <td>
                              <strong>+{row.mean_difference_hz.toFixed(3)}</strong>
                            </td>
                            <td className="mono">
                              {row.bh_fdr_q !== undefined
                                ? row.bh_fdr_q.toExponential(3)
                                : t("noneDash")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}

              <div className="notice-box">
                <strong>{t("painLimitsTitle")}: </strong>
                {t("painLimitsBody")}
              </div>
            </>
          )}
        </>
      )}

      {activeSubTab === "metabolic" && (
        <>
          {metConf.length === 0 ? (
            <div className="card">
              <div className="empty-state">
                <strong>{t("modulesMissingTitle")}</strong>
                <p style={{ marginBottom: 0 }}>{t("modulesMissingBody")}</p>
              </div>
            </div>
          ) : (
            <>
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>{t("metBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      flywire_fafb_v630 · shiu2024_lif · P4-MET-001 (N=30)
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <StatusBadge label={t("stateExperimental")} tone="info" />
                    <StatusBadge label={t("ruoBadge")} tone="ruo" />
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() =>
                        onExploreCircuit3D({
                          datasetId: "flywire_fafb_v630",
                          seedIds: "720575940660219265, 720575940645521262",
                          hops: 1,
                          direction: "incoming",
                          minSynapses: 5,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>
                <div className="grid-2">
                  <div>
                    <h3>{t("metChartContrastsTitle")}</h3>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("metChartContrastsTitle")}
                      traces={metContrastTraces}
                      layout={{
                        height: 330,
                        yaxis: { title: t("chartYAxisDeltaHz"), rangemode: "tozero" },
                        xaxis: { tickangle: -20 },
                        margin: { l: 55, r: 20, t: 25, b: 95 },
                      }}
                    />
                  </div>
                  {Object.keys(metRob).length > 0 && (
                    <div>
                      <h3>{t("metChartRobustTitle")}</h3>
                      <PlotlyChart
                        theme={theme}
                        ariaLabel={t("metChartRobustTitle")}
                        traces={metRobustTraces}
                        layout={{
                          barmode: "group",
                          height: 330,
                          yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                          margin: { l: 55, r: 20, t: 25, b: 60 },
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simpleMetTitle")}: </strong>
                  {t("simpleMetSummary")}
                </div>
              )}

              {uiMode === "expert" ? (
                <div className="card">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{t("colContrast")}</th>
                          <th>{t("colNeuron")}</th>
                          <th>{t("colBaseMean")}</th>
                          <th>{t("colTreatMean")}</th>
                          <th>{t("colDelta")}</th>
                          <th>{t("colCi95")}</th>
                          <th>{t("colPval")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metConf.map((m) => {
                          const base = m.condition_summaries[m.baseline_condition];
                          const treat = m.condition_summaries[m.treatment_condition];
                          return (
                            <tr key={m.analysis_key}>
                              <td className="mono">{m.analysis_key}</td>
                              <td className="mono">{m.target_neuron_id}</td>
                              <td>
                                {base
                                  ? `${base.mean_hz.toFixed(3)} ± ${base.sd_hz.toFixed(3)}`
                                  : t("noneDash")}
                              </td>
                              <td>
                                {treat
                                  ? `${treat.mean_hz.toFixed(3)} ± ${treat.sd_hz.toFixed(3)}`
                                  : t("noneDash")}
                              </td>
                              <td>
                                <strong>+{m.paired_metrics.mean_difference_hz.toFixed(3)}</strong> ±{" "}
                                {m.paired_metrics.sd_difference_hz.toFixed(3)}
                              </td>
                              <td className="mono">
                                [{m.paired_metrics.bootstrap_ci95_low_hz.toFixed(3)},{" "}
                                {m.paired_metrics.bootstrap_ci95_high_hz.toFixed(3)}]
                              </td>
                              <td className="mono">
                                {m.paired_metrics.permutation_test
                                  ? m.paired_metrics.permutation_test.two_sided_p_value.toExponential(
                                      3,
                                    )
                                  : t("noneDash")}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <details className="tech-details">
                  <summary>{t("showTechDetails")}</summary>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{t("colContrast")}</th>
                          <th>{t("colNeuron")}</th>
                          <th>{t("colDelta")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metConf.map((m) => (
                          <tr key={m.analysis_key}>
                            <td className="mono">{m.analysis_key}</td>
                            <td className="mono">{m.target_neuron_id}</td>
                            <td>
                              <strong>+{m.paired_metrics.mean_difference_hz.toFixed(3)}</strong>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}
            </>
          )}
        </>
      )}

      {activeSubTab === "benchmark" && (
        <div className="card">
          <div className="card-header">
            <div>
              <h2>{t("modShiuName")}</h2>
              <p className="card-subtitle">{t("modShiuDesc")}</p>
            </div>
            <button type="button" className="btn" onClick={onJumpToResults}>
              {t("navResults")}
            </button>
          </div>
          {!benchmarks[0] ? (
            <div className="empty-state">{t("noBenchmarkMsg")}</div>
          ) : (
            <p className="mono" style={{ margin: 0 }}>
              {benchmarks[0].report.benchmark_id} · overall_passed=
              {String(benchmarks[0].report.overall_passed)} · failed_run_count=
              {benchmarks[0].report.failed_run_count}
            </p>
          )}
        </div>
      )}

      {activeSubTab === "planned" && (
        <div className="grid-2">
          {plannedModules.map((mod) => {
            const descMap: Record<string, [string, string]> = {
              sleep: [t("modSleepName"), t("modSleepDesc")],
              addiction: [t("modAddictionName"), t("modAddictionDesc")],
              neuro: [t("modNeuroName"), t("modNeuroDesc")],
              pharma: [t("modPharmaName"), t("modPharmaDesc")],
              stress: [t("modStressName"), t("modStressDesc")],
            };
            const pair = descMap[mod.module_id] ?? [mod.module_id, ""];
            return (
              <div key={mod.module_id} className="card">
                <div className="card-header">
                  <div>
                    <h3>{pair[0]}</h3>
                    <p className="card-subtitle mono">{mod.phase.toUpperCase()}</p>
                  </div>
                  <StatusBadge label={t("statePlanned")} tone="neutral" />
                </div>
                <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  <strong>{t("plannedGateLabel")}: </strong>
                  {pair[1]}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
