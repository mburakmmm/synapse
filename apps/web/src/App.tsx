import React, { useCallback, useEffect, useState } from "react";
import {
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
  type ProtocolSummary,
  type RunSummary,
  type StudiesResponse,
} from "./api";
import {
  DatasetsIcon,
  JobsIcon,
  ModelsIcon,
  ModulesIcon,
  MoonIcon,
  OverviewIcon,
  RefreshIcon,
  ResultsIcon,
  SunIcon,
  SynapseLogoIcon,
  WarningIcon,
} from "./components/Icons";
import { StatusBadge } from "./components/StatusBadge";
import { useI18n } from "./i18n/LanguageContext";
import { DatasetsView, type CircuitPresetRequest } from "./views/DatasetsView";
import { JobsRunsView } from "./views/JobsRunsView";
import { ModelsProtocolsView } from "./views/ModelsProtocolsView";
import { ModulesView, type ModuleSectionTab } from "./views/ModulesView";
import { OverviewView, type WorkspaceTabId } from "./views/OverviewView";
import { ResultsExportsView } from "./views/ResultsExportsView";

export type UiMode = "simple" | "expert";

const THEME_STORAGE_KEY = "synapse.theme";
const MODE_STORAGE_KEY = "synapse.uiMode";

function resolveInitialTheme(): "dark" | "light" {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
  } catch {
    // Ignore storage restriction errors.
  }
  return "dark";
}

function resolveInitialUiMode(): UiMode {
  try {
    const saved = window.localStorage.getItem(MODE_STORAGE_KEY);
    if (saved === "expert" || saved === "simple") {
      return saved;
    }
  } catch {
    // Ignore storage restriction errors.
  }
  return "simple";
}

export const App: React.FC = () => {
  const { locale, setLocale, t } = useI18n();
  const [theme, setTheme] = useState<"dark" | "light">(resolveInitialTheme);
  const [uiMode, setUiModeState] = useState<UiMode>(resolveInitialUiMode);
  const [tab, setTab] = useState<WorkspaceTabId>("overview");
  const [moduleSubTab, setModuleSubTab] = useState<ModuleSectionTab>("pain");
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [studies, setStudies] = useState<StudiesResponse | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [backends, setBackends] = useState<BackendSummary[]>([]);
  const [protocols, setProtocols] = useState<ProtocolSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsTotal, setRunsTotal] = useState<number>(0);
  const [benchmarks, setBenchmarks] = useState<BenchmarkEnvelope[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisSummaryItem[]>([]);
  const [exportsList, setExportsList] = useState<ExportBundleItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);

  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [selectedProtocol, setSelectedProtocol] = useState<string>("");
  const [circuitPreset, setCircuitPreset] = useState<CircuitPresetRequest | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Ignore storage errors.
    }
  }, [theme]);

  const setUiMode = useCallback((next: UiMode) => {
    setUiModeState(next);
    if (next === "simple") {
      setTab((prev) => (prev === "models" || prev === "jobs" ? "overview" : prev));
    }
    try {
      window.localStorage.setItem(MODE_STORAGE_KEY, next);
    } catch {
      // Ignore storage errors.
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setErrorMsg(null);
    setLoading(true);
    try {
      const fastPromise = Promise.all([
        api.health(),
        api.datasets(),
        api.models(),
        api.protocols(),
        api.jobs(),
        api.audit(),
        api.studies().catch(() => null),
      ]).then(([h, ds, mod, proto, j, au, st]) => {
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
        setAuditEvents(au.events);
        if (st) {
          setStudies(st);
        }
      });

      const heavyPromise = Promise.all([
        api.runs({ limit: 50 }),
        api.benchmarks(),
        api.analyses(),
        api.exports(),
      ]).then(([r, bm, an, ex]) => {
        setRuns(r.runs);
        setRunsTotal(r.total);
        setBenchmarks(bm.benchmarks);
        setAnalyses(an.analyses);
        setExportsList(ex.exports);
      });

      await fastPromise;
      setLoading(false);
      await heavyPromise;
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load API workspace");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const navItems: Array<{
    id: WorkspaceTabId;
    label: string;
    sub: string;
    icon: React.ReactNode;
  }> =
    uiMode === "simple"
      ? [
          {
            id: "overview",
            label: t("navHomeSimple"),
            sub: t("navHomeSimpleSub"),
            icon: <OverviewIcon />,
          },
          {
            id: "modules",
            label: t("navStoriesSimple"),
            sub: t("navStoriesSimpleSub"),
            icon: <ModulesIcon />,
          },
          {
            id: "datasets",
            label: t("navCircuitSimple"),
            sub: t("navCircuitSimpleSub"),
            icon: <DatasetsIcon />,
          },
          {
            id: "results",
            label: t("navReportsSimple"),
            sub: t("navReportsSimpleSub"),
            icon: <ResultsIcon />,
          },
        ]
      : [
          {
            id: "overview",
            label: t("navOverview"),
            sub: t("navOverviewSub"),
            icon: <OverviewIcon />,
          },
          {
            id: "modules",
            label: t("navModules"),
            sub: t("navModulesSub"),
            icon: <ModulesIcon />,
          },
          {
            id: "datasets",
            label: t("navDatasets"),
            sub: t("navDatasetsSub"),
            icon: <DatasetsIcon />,
          },
          {
            id: "models",
            label: t("navModels"),
            sub: t("navModelsSub"),
            icon: <ModelsIcon />,
          },
          {
            id: "jobs",
            label: t("navJobs"),
            sub: t("navJobsSub"),
            icon: <JobsIcon />,
          },
          {
            id: "results",
            label: t("navResults"),
            sub: t("navResultsSub"),
            icon: <ResultsIcon />,
          },
        ];

  const handleNavigateModule = (moduleId: string) => {
    if (moduleId === "pharma") setModuleSubTab("pharma");
    else if (moduleId === "neuro") setModuleSubTab("neuro");
    else if (moduleId === "addiction") setModuleSubTab("addiction");
    else if (moduleId === "sleep") setModuleSubTab("sleep");
    else if (moduleId === "pain") setModuleSubTab("pain");
    else if (moduleId === "metabolic") setModuleSubTab("metabolic");
    else if (moduleId === "shiu2024_benchmark") setModuleSubTab("benchmark");
    else setModuleSubTab("planned");
    setTab("modules");
  };

  const handleExploreCircuit3D = (preset: Omit<CircuitPresetRequest, "nonce">) => {
    setSelectedDataset(preset.datasetId);
    setCircuitPreset({ ...preset, nonce: Date.now() });
    setTab("datasets");
  };

  return (
    <div className="workbench-layout">
      <aside className="sidebar">
        <div>
          <div className="brand-box">
            <div className="brand-mark">
              <SynapseLogoIcon size={20} />
            </div>
            <div>
              <p className="brand-title">{t("brandName")}</p>
              <p className="brand-sub">{t("brandTagline")}</p>
            </div>
          </div>

          <nav
            className="sidebar-nav"
            role="tablist"
            aria-label={t("navLabel")}
            style={{ marginTop: 14 }}
          >
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                className="nav-item"
                aria-selected={tab === item.id}
                onClick={() => setTab(item.id)}
              >
                <span className="nav-item-icon">{item.icon}</span>
                <span className="nav-item-text">
                  <span className="nav-item-label">{item.label}</span>
                  <span className="nav-item-sub">{item.sub}</span>
                </span>
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-footer">
          {uiMode === "simple" && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setUiMode("expert")}
            >
              {t("modeExpert")} →
            </button>
          )}
          <div className="sidebar-host-pill">
            <StatusBadge
              label={health ? t("connected") : t("connecting")}
              tone={health ? "ok" : "warn"}
            />
            <span className="mono">
              {t("loopbackHost")}: {health?.bind_host ?? "127.0.0.1"}
            </span>
          </div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title-group">
            <h1 className="topbar-title">{t("headerTitle")}</h1>
            <p className="topbar-subtitle">{t("headerSubtitle")}</p>
          </div>

          <div className="topbar-controls">
            <StatusBadge label={t("ruoBadge")} tone="ruo" />

            <div className="segmented" role="group" aria-label={t("uiModeLabel")}>
              <button
                type="button"
                className="seg-btn"
                aria-pressed={uiMode === "simple"}
                onClick={() => setUiMode("simple")}
              >
                {t("modeSimple")}
              </button>
              <button
                type="button"
                className="seg-btn"
                aria-pressed={uiMode === "expert"}
                onClick={() => setUiMode("expert")}
              >
                {t("modeExpert")}
              </button>
            </div>

            <div className="segmented" role="group" aria-label={t("langLabel")}>
              <button
                type="button"
                className="seg-btn"
                aria-pressed={locale === "tr"}
                onClick={() => setLocale("tr")}
              >
                TR
              </button>
              <button
                type="button"
                className="seg-btn"
                aria-pressed={locale === "en"}
                onClick={() => setLocale("en")}
              >
                EN
              </button>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              aria-label={theme === "dark" ? t("switchToLight") : t("switchToDark")}
              onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
              <span>{theme === "dark" ? t("themeLight") : t("themeDark")}</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void refreshAll()}
            >
              <RefreshIcon />
              <span>{loading ? t("refreshing") : t("refresh")}</span>
            </button>
          </div>
        </header>

        <main className="content-container">
          {errorMsg && (
            <div className="alert" role="alert">
              <WarningIcon />
              <span>{errorMsg}</span>
            </div>
          )}

          {tab === "overview" && (
            <OverviewView
              uiMode={uiMode}
              health={health}
              datasets={datasets}
              modules={studies?.modules ?? []}
              studies={studies}
              runs={runs}
              runsTotal={runsTotal}
              benchmarks={benchmarks}
              analyses={analyses}
              exportsList={exportsList}
              auditEvents={auditEvents}
              onNavigateModule={handleNavigateModule}
              onExploreCircuit3D={handleExploreCircuit3D}
              onSwitchExpert={() => setUiMode("expert")}
            />
          )}

          {tab === "modules" && (
            <ModulesView
              uiMode={uiMode}
              studies={studies}
              benchmarks={benchmarks}
              theme={theme}
              activeSubTab={moduleSubTab}
              onSelectSubTab={setModuleSubTab}
              onJumpToResults={() => setTab("results")}
              onExploreCircuit3D={handleExploreCircuit3D}
            />
          )}

          {tab === "datasets" && (
            <DatasetsView
              uiMode={uiMode}
              datasets={datasets}
              selectedDataset={selectedDataset}
              onSelectDataset={setSelectedDataset}
              theme={theme}
              presetRequest={circuitPreset}
              onError={setErrorMsg}
            />
          )}

          {tab === "models" && (
            <ModelsProtocolsView
              models={models}
              backends={backends}
              protocols={protocols}
              selectedProtocol={selectedProtocol}
              onSelectProtocol={setSelectedProtocol}
              onRefresh={refreshAll}
              onError={setErrorMsg}
            />
          )}

          {tab === "jobs" && (
            <JobsRunsView
              selectedProtocol={selectedProtocol}
              selectedDataset={selectedDataset}
              jobs={jobs}
              runs={runs}
              runsTotal={runsTotal}
              auditEvents={auditEvents}
              onRefresh={refreshAll}
              onError={setErrorMsg}
            />
          )}

          {tab === "results" && (
            <ResultsExportsView
              uiMode={uiMode}
              benchmarks={benchmarks}
              analyses={analyses}
              exportsList={exportsList}
              theme={theme}
              onError={setErrorMsg}
            />
          )}
        </main>
      </div>
    </div>
  );
};
