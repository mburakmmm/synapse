import React, { useState } from "react";
import type {
  AnalysisSummaryItem,
  AuditEventItem,
  BenchmarkEnvelope,
  DatasetSummary,
  ExportBundleItem,
  HealthResponse,
  ResearchModuleItem,
  RunSummary,
  StudiesResponse,
} from "../api";
import type { UiMode } from "../App";
import { ShieldIcon } from "../components/Icons";
import { StatusBadge, type BadgeTone } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";
import type { TranslationKey } from "../i18n/translations";
import type { CircuitPresetRequest } from "./DatasetsView";

export type WorkspaceTabId =
  | "overview"
  | "modules"
  | "datasets"
  | "models"
  | "jobs"
  | "results";

interface OverviewViewProps {
  uiMode: UiMode;
  health: HealthResponse | null;
  datasets: DatasetSummary[];
  modules: ResearchModuleItem[];
  studies: StudiesResponse | null;
  runs: RunSummary[];
  runsTotal: number;
  benchmarks: BenchmarkEnvelope[];
  analyses: AnalysisSummaryItem[];
  exportsList: ExportBundleItem[];
  auditEvents: AuditEventItem[];
  onNavigateModule: (moduleId: string) => void;
  onExploreCircuit3D: (preset: Omit<CircuitPresetRequest, "nonce">) => void;
  onSwitchExpert: () => void;
}

const MODULE_META: Record<string, { nameKey: TranslationKey; descKey: TranslationKey }> = {
  shiu2024_benchmark: { nameKey: "modShiuName", descKey: "modShiuDesc" },
  metabolic: { nameKey: "modMetName", descKey: "modMetDesc" },
  pain: { nameKey: "modPainName", descKey: "modPainDesc" },
  sleep: { nameKey: "modSleepName", descKey: "modSleepDesc" },
  addiction: { nameKey: "modAddictionName", descKey: "modAddictionDesc" },
  neuro: { nameKey: "modNeuroName", descKey: "modNeuroDesc" },
  pharma: { nameKey: "modPharmaName", descKey: "modPharmaDesc" },
  stress: { nameKey: "modStressName", descKey: "modStressDesc" },
};

const GLOSSARY_KEYS: Array<{
  id: string;
  titleKey: TranslationKey;
  defKey: TranslationKey;
}> = [
  { id: "connectome", titleKey: "glossConnectomeTitle", defKey: "glossConnectomeDef" },
  { id: "gaba", titleKey: "glossGabaTitle", defKey: "glossGabaDef" },
  { id: "ach", titleKey: "glossAchTitle", defKey: "glossAchDef" },
  { id: "ctrl", titleKey: "glossCtrlTitle", defKey: "glossCtrlDef" },
  { id: "sham", titleKey: "glossShamTitle", defKey: "glossShamDef" },
  { id: "hz", titleKey: "glossHzTitle", defKey: "glossHzDef" },
  { id: "circadian", titleKey: "glossCircadianTitle", defKey: "glossCircadianDef" },
  { id: "homeostat", titleKey: "glossHomeostatTitle", defKey: "glossHomeostatDef" },
  { id: "plasticity", titleKey: "glossPlasticityTitle", defKey: "glossPlasticityDef" },
  { id: "extinction", titleKey: "glossExtinctionTitle", defKey: "glossExtinctionDef" },
  { id: "ablation", titleKey: "glossAblationTitle", defKey: "glossAblationDef" },
  { id: "fragmentation", titleKey: "glossFragTitle", defKey: "glossFragDef" },
];

export function moduleStateBadge(
  uiState: string,
  t: (key: TranslationKey) => string,
): { label: string; tone: BadgeTone } {
  switch (uiState) {
    case "reproduced":
      return { label: t("stateReproduced"), tone: "ok" };
    case "validated_for_declared_endpoint":
      return { label: t("stateValidatedEndpoint"), tone: "ok" };
    case "experimental":
      return { label: t("stateExperimental"), tone: "info" };
    default:
      return { label: t("statePlanned"), tone: "neutral" };
  }
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  uiMode,
  health,
  datasets,
  modules,
  studies,
  runs,
  runsTotal,
  benchmarks,
  analyses,
  exportsList,
  auditEvents,
  onNavigateModule,
  onExploreCircuit3D,
  onSwitchExpert,
}) => {
  const { t } = useI18n();
  const [selectedGlossId, setSelectedGlossId] = useState<string>("connectome");
  const normalizedCount = datasets.filter((d) => d.on_disk).length;
  const activeModulesCount = modules.filter((m) => m.ui_state !== "planned").length;

  const painPrimary = studies?.pain.confirmatory?.primary_contrasts.find(
    (c) => c.contrast_name === "p1_523539_edge_mask_vs_base",
  );
  const metPrimary = studies?.metabolic.confirmatory.find((c) =>
    c.analysis_key.includes("mn9r_gain_1p50"),
  );
  const sleepPrimary = studies?.sleep?.pilot?.contrasts.find(
    (c) => c.contrast_name === "analysis_22794_clock_vs_base",
  );
  const sleepL3Gate = studies?.sleep?.l3_gate ?? null;
  const addictionL2Gate = studies?.addiction?.l2_gate ?? null;
  const addictionPrimary =
    studies?.addiction?.pilot?.contrasts.find((c) => c.contrast_name.includes("acq")) ??
    studies?.addiction?.pilot?.contrasts[0];
  const neuroL0Gate = studies?.neuro?.l0_gate ?? null;
  const neuroL0Summary = studies?.neuro?.l0_summary ?? null;
  const neuroPrimary =
    studies?.neuro?.pilot?.contrasts.find((c) =>
      c.contrast_name.includes("mn9r_cell_loss_top12_vs_intact"),
    ) ?? studies?.neuro?.pilot?.contrasts[0];
  const primaryBench = benchmarks[0]?.report;

  if (uiMode === "simple") {
    const activeGloss = GLOSSARY_KEYS.find((g) => g.id === selectedGlossId) ?? GLOSSARY_KEYS[0];
    return (
      <section role="tabpanel" aria-label={t("navHomeSimple")}>
        <div className="hero-card">
          <div>
            <h2>{t("simpleHeroTitle")}</h2>
            <p>{t("simpleHeroBody")}</p>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <StatusBadge label={t("ruoBadge")} tone="ruo" />
            <StatusBadge
              label={health ? t("connected") : t("connecting")}
              tone={health ? "ok" : "warn"}
            />
          </div>
        </div>

        <div className="notice-box">{t("simpleRuoPlain")}</div>

        <div>
          <h2 style={{ margin: "4px 0 12px", fontSize: "1.05rem" }}>{t("simpleStoriesTitle")}</h2>
          <div className="story-grid">
            <div className="story-card">
              <div>
                <div className="card-header" style={{ marginBottom: 6 }}>
                  <h3>{t("simplePainTitle")}</h3>
                  <StatusBadge label={t("stateExperimental")} tone="info" />
                </div>
                <div className="story-card-metric">
                  {painPrimary
                    ? `+${painPrimary.mean_difference_hz.toFixed(1)} Hz`
                    : t("noneDash")}
                </div>
                <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginBottom: 0 }}>
                  {painPrimary ? t("simplePainSummary") : t("simpleMissingNote")}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigateModule("pain")}
                >
                  {t("readStoryBtn")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
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
                  {t("open3dBtn")}
                </button>
              </div>
            </div>

            <div className="story-card">
              <div>
                <div className="card-header" style={{ marginBottom: 6 }}>
                  <h3>{t("simpleMetTitle")}</h3>
                  <StatusBadge label={t("stateExperimental")} tone="info" />
                </div>
                <div className="story-card-metric">
                  {metPrimary
                    ? `+${metPrimary.paired_metrics.mean_difference_hz.toFixed(1)} Hz`
                    : t("noneDash")}
                </div>
                <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginBottom: 0 }}>
                  {metPrimary ? t("simpleMetSummary") : t("simpleMissingNote")}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigateModule("metabolic")}
                >
                  {t("readStoryBtn")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
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
                  {t("open3dBtn")}
                </button>
              </div>
            </div>

            <div className="story-card">
              <div>
                <div className="card-header" style={{ marginBottom: 6 }}>
                  <h3>{t("simpleSleepTitle")}</h3>
                  <StatusBadge
                    label={sleepL3Gate?.overall_passed ? t("stateExperimental") : t("statePlanned")}
                    tone={sleepL3Gate?.overall_passed ? "info" : "neutral"}
                  />
                </div>
                <div className="story-card-metric">
                  {sleepPrimary
                    ? `${sleepPrimary.mean_difference_hz.toFixed(1)} Hz`
                    : sleepL3Gate?.gates.dd_free_running_and_convergence.tau_dd_coarse_h
                      ? `${sleepL3Gate.gates.dd_free_running_and_convergence.tau_dd_coarse_h.toFixed(2)} h`
                      : t("noneDash")}
                </div>
                <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginBottom: 0 }}>
                  {sleepPrimary || sleepL3Gate ? t("simpleSleepSummary") : t("simpleMissingNote")}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigateModule("sleep")}
                >
                  {t("readStoryBtn")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    onExploreCircuit3D({
                      datasetId: "malecns_v1_0",
                      seedIds: "10324, 15016, 114115, 112789, 10043",
                      hops: 1,
                      direction: "both",
                      minSynapses: 25,
                      maxNodes: 75,
                    })
                  }
                >
                  {t("open3dBtn")}
                </button>
              </div>
            </div>

            <div className="story-card">
              <div>
                <div className="card-header" style={{ marginBottom: 6 }}>
                  <h3>{t("simpleAddictionTitle")}</h3>
                  <StatusBadge
                    label={addictionL2Gate?.overall_passed ? t("stateExperimental") : t("statePlanned")}
                    tone={addictionL2Gate?.overall_passed ? "info" : "neutral"}
                  />
                </div>
                <div className="story-card-metric">
                  {addictionPrimary
                    ? `${addictionPrimary.mean_difference_hz >= 0 ? "+" : ""}${addictionPrimary.mean_difference_hz.toFixed(1)} Hz`
                    : addictionL2Gate
                      ? `+${addictionL2Gate.gates.acquisition_specificity.pi_acq.toFixed(2)} PI`
                      : t("noneDash")}
                </div>
                <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginBottom: 0 }}>
                  {addictionPrimary || addictionL2Gate ? t("simpleAddictionSummary") : t("simpleMissingNote")}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigateModule("addiction")}
                >
                  {t("readStoryBtn")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    onExploreCircuit3D({
                      datasetId: "malecns_v1_0",
                      seedIds: "522749, 522444, 13728, 10267, 512788, 10977",
                      hops: 1,
                      direction: "both",
                      minSynapses: 30,
                      maxNodes: 75,
                    })
                  }
                >
                  {t("open3dBtn")}
                </button>
              </div>
            </div>

            <div className="story-card">
              <div>
                <div className="card-header" style={{ marginBottom: 6 }}>
                  <h3>{t("simpleNeuroTitle")}</h3>
                  <StatusBadge
                    label={neuroL0Gate?.overall_passed ? t("stateExperimental") : t("statePlanned")}
                    tone={neuroL0Gate?.overall_passed ? "info" : "neutral"}
                  />
                </div>
                <div className="story-card-metric">
                  {neuroPrimary
                    ? `${neuroPrimary.mean_difference_hz >= 0 ? "+" : ""}${neuroPrimary.mean_difference_hz.toFixed(1)} Hz`
                    : neuroL0Summary
                      ? `${(
                          (neuroL0Summary.curve_points.find(
                            (p) => p.arm_type === "targeted_cell_loss" && p.step_k === 12,
                          )?.weighted_eff_ratio ?? 1) * 100
                        ).toFixed(1)}% L0 Eff`
                      : t("noneDash")}
                </div>
                <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginBottom: 0 }}>
                  {neuroPrimary || neuroL0Gate ? t("simpleNeuroSummary") : t("simpleMissingNote")}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigateModule("neuro")}
                >
                  {t("readStoryBtn")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    onExploreCircuit3D({
                      datasetId: "flywire_fafb_v630",
                      seedIds:
                        "720575940660219265, 720575940645521262, 720575940623211725, 720575940619853515, 720575940607272649, 720575940626038714",
                      hops: 1,
                      direction: "both",
                      minSynapses: 15,
                      maxNodes: 75,
                    })
                  }
                >
                  {t("open3dBtn")}
                </button>
              </div>
            </div>

            <div className="story-card">
              <div>
                <div className="card-header" style={{ marginBottom: 6 }}>
                  <h3>{t("simpleBenchTitle")}</h3>
                  <StatusBadge
                    label={primaryBench?.overall_passed ? t("stateReproduced") : t("statePlanned")}
                    tone={primaryBench?.overall_passed ? "ok" : "neutral"}
                  />
                </div>
                <div className="story-card-metric">
                  {primaryBench
                    ? `${primaryBench.failed_run_count} failed`
                    : t("noneDash")}
                </div>
                <p style={{ fontSize: "0.83rem", color: "var(--text-secondary)", marginBottom: 0 }}>
                  {primaryBench ? t("simpleBenchSummary") : t("simpleMissingNote")}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onNavigateModule("shiu2024_benchmark")}
                >
                  {t("readStoryBtn")}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>{t("glossaryTitle")}</h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onSwitchExpert}
            >
              {t("modeExpert")}
            </button>
          </div>
          <div className="pill-group" style={{ marginBottom: 8 }}>
            {GLOSSARY_KEYS.map((item) => (
              <button
                key={item.id}
                type="button"
                className="pill-btn"
                aria-pressed={activeGloss.id === item.id}
                onClick={() => setSelectedGlossId(item.id)}
              >
                {t(item.titleKey)}
              </button>
            ))}
          </div>
          <div className="glossary-box">
            <strong>{t(activeGloss.titleKey)}: </strong>
            <span>{t(activeGloss.defKey)}</span>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section role="tabpanel" aria-label={t("navOverview")}>
      <div className="hero-card">
        <div>
          <h2>{t("overviewHeroTitle")}</h2>
          <p>{t("overviewHeroBody")}</p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <StatusBadge label={t("ruoBadge")} tone="ruo" />
          <StatusBadge
            label={health ? t("connected") : t("connecting")}
            tone={health ? "ok" : "warn"}
          />
        </div>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">{t("kpiDatasets")}</div>
          <div className="kpi-value">{normalizedCount}</div>
          <div className="kpi-sub">
            {datasets.length} {t("kpiDatasetsSub")}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">{t("kpiModules")}</div>
          <div className="kpi-value">{activeModulesCount}</div>
          <div className="kpi-sub">
            {modules.length} {t("kpiModulesSub")}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">{t("kpiRuns")}</div>
          <div className="kpi-value">{runsTotal || runs.length}</div>
          <div className="kpi-sub">
            {benchmarks.length} · {analyses.length} {t("kpiRunsSub")}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">{t("kpiExports")}</div>
          <div className="kpi-value">{exportsList.length}</div>
          <div className="kpi-sub">{t("kpiExportsSub")}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h2>{t("matrixTitle")}</h2>
            <p className="card-subtitle">{t("matrixSubtitle")}</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("colModule")}</th>
                <th>{t("colPhase")}</th>
                <th>{t("colUiState")}</th>
                <th>{t("colDataset")}</th>
                <th>{t("colProtocol")}</th>
                <th>{t("colArtifacts")}</th>
                <th>{t("colAction")}</th>
              </tr>
            </thead>
            <tbody>
              {modules.map((mod) => {
                const meta = MODULE_META[mod.module_id];
                const st = moduleStateBadge(mod.ui_state, t);
                return (
                  <tr key={mod.module_id}>
                    <td>
                      <strong>{meta ? t(meta.nameKey) : mod.module_id}</strong>
                      {meta && (
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                          {t(meta.descKey)}
                        </div>
                      )}
                    </td>
                    <td className="mono">{mod.phase.toUpperCase()}</td>
                    <td>
                      <StatusBadge label={st.label} tone={st.tone} />
                    </td>
                    <td className="mono">{mod.dataset_id ?? t("noneDash")}</td>
                    <td className="mono">{mod.protocol_id ?? t("noneDash")}</td>
                    <td>
                      <StatusBadge
                        label={mod.available_on_disk ? t("onDiskYes") : t("onDiskNo")}
                        tone={mod.available_on_disk ? "ok" : "neutral"}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => onNavigateModule(mod.module_id)}
                      >
                        {t("openModule")}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>{t("guardrailsTitle")}</h3>
          <StatusBadge label={t("bioRuoBadge")} tone="warn" />
        </div>
        <div className="grid-4">
          <div className="guardrail-card">
            <h4>
              <ShieldIcon /> {t("guardrail1Title")}
            </h4>
            <p>{t("guardrail1Body")}</p>
          </div>
          <div className="guardrail-card">
            <h4>
              <ShieldIcon /> {t("guardrail2Title")}
            </h4>
            <p>{t("guardrail2Body")}</p>
          </div>
          <div className="guardrail-card">
            <h4>
              <ShieldIcon /> {t("guardrail3Title")}
            </h4>
            <p>{t("guardrail3Body")}</p>
          </div>
          <div className="guardrail-card">
            <h4>
              <ShieldIcon /> {t("guardrail4Title")}
            </h4>
            <p>{t("guardrail4Body")}</p>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <h3>{t("sysHealthTitle")}</h3>
            <StatusBadge
              label={health ? health.status.toUpperCase() : t("connecting")}
              tone={health ? "ok" : "warn"}
            />
          </div>
          <div className="meta-strip">
            <span>
              {t("loopbackHost")}: <strong className="mono">{health?.bind_host ?? "127.0.0.1"}</strong>
            </span>
            <span>
              {t("apiVersion")}: <strong className="mono">{health?.api_version ?? "v1"}</strong>
            </span>
            {health?.storage?.disk_free_gb !== null && health?.storage?.disk_free_gb !== undefined && (
              <span>
                {t("diskFreeLabel")}:{" "}
                <strong className="mono">
                  {health.storage.disk_free_gb} / {health.storage.disk_total_gb} GB
                </strong>
              </span>
            )}
          </div>
          <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-secondary)" }}>
            {t("ruoPolicyLabel")}: {health?.ruo_notice ?? t("ruoBadge")}
          </p>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>
              {t("recentAuditTitle")} ({auditEvents.length})
            </h3>
          </div>
          {auditEvents.length === 0 ? (
            <div className="empty-state">{t("noAuditEvents")}</div>
          ) : (
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
                  {auditEvents.slice(0, 6).map((ev) => (
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
          )}
        </div>
      </div>
    </section>
  );
};
