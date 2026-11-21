import React, { useState } from "react";
import {
  api,
  type BackendSummary,
  type ModelSummary,
  type ProtocolContentResponse,
  type ProtocolSummary,
} from "../api";
import { CodeIcon } from "../components/Icons";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";

interface ModelsProtocolsViewProps {
  models: ModelSummary[];
  backends: BackendSummary[];
  protocols: ProtocolSummary[];
  selectedProtocol: string;
  onSelectProtocol: (relPath: string) => void;
  onRefresh: () => Promise<void>;
  onError: (msg: string | null) => void;
}

export const ModelsProtocolsView: React.FC<ModelsProtocolsViewProps> = ({
  models,
  backends,
  protocols,
  selectedProtocol,
  onSelectProtocol,
  onRefresh,
  onError,
}) => {
  const { t } = useI18n();
  const [freezeConfirmed, setFreezeConfirmed] = useState<boolean>(false);
  const [protocolActionResult, setProtocolActionResult] = useState<string | null>(null);
  const [yamlContent, setYamlContent] = useState<ProtocolContentResponse | null>(null);

  const [draftYamlText, setDraftYamlText] = useState<string>(
    "schema_version: '1.0'\nprotocol_id: DRAFT-TEST-001\nrevision: 1\nstatus: draft\nanalysis_intent: exploratory\nquestion: Exploratory draft schema check.\nhypothesis: Candidate hypothesis.\nbiological_unit: single_specimen\nsimulation_unit: paired_seed_run\nsources:\n  - dataset_id: synthetic_microcircuit_v1\n    release: '1.0'\n    manifest_sha256: UNRESOLVED\nmodel:\n  id: shiu2024_lif\n  revision: '1.0'\n  parameter_manifest_sha256: UNRESOLVED\nconditions:\n  - id: baseline\n    interventions:\n      - kind: sham\nseeds:\n  master: 2026\n  replicates: 2\nanalysis:\n  primary_endpoints: []\noutputs:\n  base_dir: runs/draft_check\n",
  );
  const [allowUnresolvedDraft, setAllowUnresolvedDraft] = useState<boolean>(true);
  const [draftValidationOut, setDraftValidationOut] = useState<string | null>(null);

  const handleValidateProtocol = async () => {
    if (!selectedProtocol) return;
    onError(null);
    try {
      const res = await api.validateProtocol(selectedProtocol, false);
      setProtocolActionResult(JSON.stringify(res, null, 2));
    } catch (err) {
      onError(err instanceof Error ? err.message : "Protocol validation failed");
    }
  };

  const handleInspectYaml = async () => {
    if (!selectedProtocol) return;
    onError(null);
    try {
      const res = await api.protocolContent(selectedProtocol);
      setYamlContent(res);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load protocol YAML");
    }
  };

  const handleFreezeProtocol = async () => {
    if (!selectedProtocol || !freezeConfirmed) return;
    onError(null);
    try {
      const res = await api.freezeProtocol(selectedProtocol, true);
      setProtocolActionResult(JSON.stringify(res, null, 2));
      setFreezeConfirmed(false);
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Protocol freeze failed");
    }
  };

  const handleValidateDraftYaml = async () => {
    if (!draftYamlText.trim()) return;
    onError(null);
    try {
      const res = await api.validateProtocolYaml(draftYamlText, allowUnresolvedDraft);
      setDraftValidationOut(JSON.stringify(res, null, 2));
    } catch (err) {
      setDraftValidationOut(
        JSON.stringify(
          { valid: false, error: err instanceof Error ? err.message : "Validation error" },
          null,
          2,
        ),
      );
    }
  };

  return (
    <section role="tabpanel" aria-label={t("navModels")}>
      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <h2>{t("modelsTitle")}</h2>
          </div>

          {models.map((m) => (
            <div
              key={m.parameter_manifest_sha256}
              style={{
                marginBottom: 14,
                padding: 12,
                borderRadius: 10,
                background: "var(--bg-panel-subtle)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div className="card-header" style={{ marginBottom: 6 }}>
                <strong className="mono">{m.model_id}</strong>
                <StatusBadge
                  label={`solver: ${m.solver} · dg=${String(m.dg_unless_refractory)}`}
                  tone="info"
                />
              </div>
              <div className="mono" style={{ color: "var(--text-muted)", fontSize: "0.74rem" }}>
                {t("modelsManifestHash")}: {m.parameter_manifest_sha256}
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: 4 }}>
                <strong>{t("modelsSourceLabel")}: </strong>
                {m.parameter_source}
              </div>
              {m.parameters && (
                <div className="param-grid">
                  {Object.entries(m.parameters).map(([k, v]) => (
                    <div key={k} className="param-item">
                      <div className="param-item-k mono">{k}</div>
                      <div className="param-item-v mono">{String(v)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          <h3>{t("backendsTitle")}</h3>
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table>
              <thead>
                <tr>
                  <th>Backend</th>
                  <th>Device / Precision</th>
                  <th>{t("colStatus")}</th>
                </tr>
              </thead>
              <tbody>
                {backends.map((b) => (
                  <tr key={b.backend_id}>
                    <td className="mono">{b.backend_id}</td>
                    <td className="mono">
                      {b.device} ({b.precision})
                    </td>
                    <td>
                      <StatusBadge
                        label={b.verified ? t("statusVerifiedCpu") : t("statusUnverifiedGpu")}
                        tone={b.verified ? "ok" : "warn"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>{t("protocolsTitle")}</h2>
          </div>

          <div className="form-row">
            <label className="field" style={{ flex: "1 1 220px" }}>
              {t("protocolSelectLabel")}
              <select
                value={selectedProtocol}
                onChange={(e) => onSelectProtocol(e.target.value)}
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
              {t("validateBtn")}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void handleInspectYaml()}
            >
              <CodeIcon /> {t("inspectYamlBtn")}
            </button>
          </div>

          <label
            style={{
              display: "flex",
              gap: 9,
              alignItems: "center",
              marginBottom: 12,
              fontSize: "0.83rem",
              color: "var(--text-secondary)",
            }}
          >
            <input
              type="checkbox"
              checked={freezeConfirmed}
              onChange={(e) => setFreezeConfirmed(e.target.checked)}
            />
            <span>{t("freezeConfirmLabel")}</span>
          </label>

          <button
            type="button"
            className="btn"
            disabled={!freezeConfirmed || !selectedProtocol}
            onClick={() => void handleFreezeProtocol()}
          >
            {t("freezeBtn")}
          </button>

          {protocolActionResult && <pre className="code-panel mono">{protocolActionResult}</pre>}

          {yamlContent && (
            <div style={{ marginTop: 14 }}>
              <div className="card-header" style={{ marginBottom: 4 }}>
                <h3>
                  {t("protocolYamlTitle")}: <span className="mono">{yamlContent.relative_path}</span>
                </h3>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setDraftYamlText(yamlContent.yaml_text)}
                  >
                    {t("loadIntoSandbox")}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setYamlContent(null)}
                  >
                    {t("close")}
                  </button>
                </div>
              </div>
              {yamlContent.question && (
                <p
                  style={{
                    margin: "4px 0 8px",
                    fontSize: "0.82rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  <strong>{t("protocolQuestion")}: </strong>
                  {yamlContent.question}
                </p>
              )}
              <pre className="code-panel mono">{yamlContent.yaml_text}</pre>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3>{t("draftValidatorTitle")}</h3>
            <p className="card-subtitle">{t("draftValidatorSub")}</p>
          </div>
          <button
            type="button"
            className="btn"
            onClick={() => void handleValidateDraftYaml()}
          >
            {t("validateDraftYamlBtn")}
          </button>
        </div>

        <label
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            marginBottom: 10,
            fontSize: "0.82rem",
            color: "var(--text-secondary)",
          }}
        >
          <input
            type="checkbox"
            checked={allowUnresolvedDraft}
            onChange={(e) => setAllowUnresolvedDraft(e.target.checked)}
          />
          <span>{t("allowUnresolvedLabel")}</span>
        </label>

        <textarea
          className="code-editor"
          aria-label={t("draftValidatorTitle")}
          value={draftYamlText}
          onChange={(e) => setDraftYamlText(e.target.value)}
        />

        {draftValidationOut && <pre className="code-panel mono">{draftValidationOut}</pre>}
      </div>
    </section>
  );
};
