import React from "react";
import type {
  AnalysisSummaryItem,
  AuditEventItem,
  BenchmarkEnvelope,
  DatasetSummary,
  ExportBundleItem,
  HealthResponse,
  ResearchModuleItem,
  RunSummary,
} from "../api";
import { ShieldIcon } from "../components/Icons";
import { StatusBadge, type BadgeTone } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";
import type { TranslationKey } from "../i18n/translations";

export type WorkspaceTabId =
  | "overview"
  | "modules"
  | "datasets"
  | "models"
  | "jobs"
  | "results";

interface OverviewViewProps {
  health: HealthResponse | null;
  datasets: DatasetSummary[];
  modules: ResearchModuleItem[];
  runs: RunSummary[];
  runsTotal: number;
  benchmarks: BenchmarkEnvelope[];
  analyses: AnalysisSummaryItem[];
  exportsList: ExportBundleItem[];
  auditEvents: AuditEventItem[];
  onNavigateModule: (moduleId: string) => void;
}

const MODULE_META: Record<
  string,
  { nameKey: TranslationKey; descKey: TranslationKey }
> = {
  shiu2024_benchmark: { nameKey: "modShiuName", descKey: "modShiuDesc" },
  metabolic: { nameKey: "modMetName", descKey: "modMetDesc" },
  pain: { nameKey: "modPainName", descKey: "modPainDesc" },
  sleep: { nameKey: "modSleepName", descKey: "modSleepDesc" },
  addiction: { nameKey: "modAddictionName", descKey: "modAddictionDesc" },
  neuro: { nameKey: "modNeuroName", descKey: "modNeuroDesc" },
  pharma: { nameKey: "modPharmaName", descKey: "modPharmaDesc" },
  stress: { nameKey: "modStressName", descKey: "modStressDesc" },
};

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
  health,
  datasets,
  modules,
  runs,
  runsTotal,
  benchmarks,
  analyses,
  exportsList,
  auditEvents,
  onNavigateModule,
}) => {
  const { t } = useI18n();
  const normalizedCount = datasets.filter((d) => d.on_disk).length;
  const activeModulesCount = modules.filter((m) => m.ui_state !== "planned").length;

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
