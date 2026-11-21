import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { LanguageProvider } from "../i18n/LanguageContext";

function mockJsonResponse(payload: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(payload),
  } as Response);
}

function createApiFetchMock() {
  return vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
    const target = String(url);
    if (target.endsWith("/api/v1/health")) {
      return mockJsonResponse({
        status: "ok",
        api_version: "v1",
        ruo_notice: "Research Use Only",
        bind_host: "127.0.0.1",
      });
    }
    if (target.endsWith("/api/v1/studies")) {
      return mockJsonResponse({
        modules: [
          {
            module_id: "shiu2024_benchmark",
            phase: "phase2",
            ui_state: "reproduced",
            simulation_phase: "computationally_reproduced",
            dataset_id: "flywire_fafb_v630",
            protocol_id: "P2-BENCH-SHIU2024",
            available_on_disk: true,
          },
          {
            module_id: "metabolic",
            phase: "phase4",
            ui_state: "experimental",
            simulation_phase: "confirmatory_simulation_complete",
            dataset_id: "flywire_fafb_v630",
            protocol_id: "P4-MET-001",
            available_on_disk: true,
          },
          {
            module_id: "pain",
            phase: "phase5a",
            ui_state: "experimental",
            simulation_phase: "confirmatory_simulation_complete",
            dataset_id: "malecns_v1_0",
            protocol_id: "P5-PAIN-001",
            available_on_disk: true,
          },
          {
            module_id: "sleep",
            phase: "phase5b",
            ui_state: "planned",
            simulation_phase: "planned",
            dataset_id: null,
            protocol_id: null,
            available_on_disk: false,
          },
          {
            module_id: "addiction",
            phase: "phase5b",
            ui_state: "planned",
            simulation_phase: "planned",
            dataset_id: null,
            protocol_id: null,
            available_on_disk: false,
          },
        ],
        metabolic: {
          confirmatory: [
            {
              analysis_key: "analysis_mn9r_gain_1p50",
              target_neuron_id: "720575940660219265",
              baseline_condition: "sugar_50hz_baseline",
              treatment_condition: "sugar_50hz_grn_gain_1p50",
              failed_run_count: 0,
              condition_summaries: {
                sugar_50hz_baseline: { mean_hz: 20.2, sd_hz: 6.456, n_seed_replicates: 30 },
                sugar_50hz_grn_gain_1p50: { mean_hz: 51.1, sd_hz: 5.326, n_seed_replicates: 30 },
              },
              paired_metrics: {
                n_pairs: 30,
                mean_difference_hz: 30.9,
                sd_difference_hz: 7.194,
                bootstrap_ci95_low_hz: 28.233,
                bootstrap_ci95_high_hz: 33.367,
                uncertainty_interpretation: "conditional_on_model_and_seeds",
                permutation_test: { method: "monte_carlo_sign_flip", two_sided_p_value: 9.999e-5 },
              },
              provenance: {},
            },
          ],
          robustness: {},
        },
        pain: {
          confirmatory: {
            total_runs: 120,
            failed_run_count: 0,
            sham_count: 15,
            sham_max_spikes: 0,
            wall_total_s: 8271.7,
            run_wall_min_s: 178.1,
            run_wall_mean_s: 204.7,
            run_wall_max_s: 284.7,
            git_commits: ["5a878cd"],
            git_dirty_values: [false],
            primary_contrasts: [
              {
                contrast_name: "p1_523539_edge_mask_vs_base",
                neuron_id: "523539",
                baseline_condition: "mesoln_40hz_baseline",
                treatment_condition: "mesoln_40hz_acute_edge_mask",
                n_pairs: 15,
                failed_run_count: 0,
                baseline_summary: { mean_hz: 11.917, sd_hz: 2.79 },
                treatment_summary: { mean_hz: 32.583, sd_hz: 3.487 },
                mean_difference_hz: 20.667,
                sd_difference_hz: 2.907,
                bootstrap_ci95_low_hz: 19.331,
                bootstrap_ci95_high_hz: 22.167,
                permutation_p: 9.999e-5,
                bh_fdr_q: 9.999e-5,
              },
            ],
            secondary_contrasts: [],
          },
          windowed: null,
          robustness: null,
        },
      });
    }
    if (target.endsWith("/api/v1/datasets")) {
      return mockJsonResponse({
        datasets: [
          {
            dataset_id: "synthetic_microcircuit_v1",
            release: "1.0",
            species: "synthetic_test",
            sex: "unknown",
            specimen_id: "synth_01",
            is_synthetic_fixture: true,
            on_disk: true,
          },
        ],
      });
    }
    if (target.includes("/neurons")) {
      return mockJsonResponse({
        total: 1,
        offset: 0,
        limit: 25,
        is_synthetic_fixture: true,
        neurons: [
          {
            source_neuron_id: "9007199254740996",
            cell_type: "TEST_OUTPUT",
            neurotransmitter: "ACH",
          },
        ],
      });
    }
    if (target.endsWith("/api/v1/models")) {
      return mockJsonResponse({
        models: [
          {
            model_id: "shiu2024_lif",
            model_revision: "1.0",
            parameter_manifest_sha256: "abc",
            solver: "linear",
            dt_s: 0.0001,
            dg_unless_refractory: true,
            parameter_source: "Shiu 2024",
            parameters: { v_rest_v: -0.052, w_syn_v: 0.000275 },
          },
        ],
        backends: [
          {
            backend_id: "brian2_cpu",
            device: "cpu",
            precision: "float64",
            supported_solvers: ["linear"],
            verified: true,
            reproducibility_class: "deterministic_seeded_cpu_single_process",
          },
        ],
      });
    }
    if (target.endsWith("/api/v1/protocols")) {
      return mockJsonResponse({
        protocols: [
          {
            relative_path: "P0-SYNTH-001.yaml",
            protocol_id: "P0-SYNTH-001",
            revision: 1,
            status: "approved",
            analysis_intent: "exploratory",
          },
        ],
      });
    }
    if (target.includes("/api/v1/protocols/content")) {
      return mockJsonResponse({
        relative_path: "P0-SYNTH-001.yaml",
        yaml_text: "protocol_id: P0-SYNTH-001\nstatus: approved\n",
        size_bytes: 40,
        question: "Synthetic check",
      });
    }
    if (target.endsWith("/api/v1/protocols/validate")) {
      return mockJsonResponse({
        valid: true,
        protocol_id: "DRAFT-TEST-001",
        status: "draft",
        analysis_intent: "exploratory",
      });
    }
    if (target.endsWith("/api/v1/protocols/freeze")) {
      return mockJsonResponse({ frozen_path: "P0-SYNTH-001.frozen.yaml" });
    }
    if (target.endsWith("/api/v1/jobs")) {
      return mockJsonResponse({
        jobs: [
          {
            job_id: "job_running123",
            parent_job_id: null,
            idempotency_key: "idem-1",
            kind: "protocol_experiment",
            status: "running",
            attempt_number: 1,
            worker_id: "w-1",
            worker_pid: 42,
            error_message: null,
            created_at_utc: "2026-11-20T00:00:00Z",
            result: null,
          },
        ],
      });
    }
    if (target.endsWith("/api/v1/jobs/job_running123/cancel") && init?.method === "POST") {
      return mockJsonResponse({
        job: { job_id: "job_running123", status: "cancel_requested" },
      });
    }
    if (target.includes("/api/v1/runs")) {
      return mockJsonResponse({ total: 0, runs: [] });
    }
    if (target.endsWith("/api/v1/benchmarks")) {
      return mockJsonResponse({
        benchmarks: [
          {
            relative_path: "phase2_shiu2024_reproduction_r2/evaluation/benchmark_report.json",
            report: {
              benchmark_id: "SHIU2024-FEEDING-BENCHMARK",
              overall_passed: true,
              failed_run_count: 0,
              provenance: {
                dataset_id: "flywire_fafb_v630",
                dataset_release: "v630",
                model_id: "shiu2024_lif",
                protocol_id: "P2-BENCH-SHIU2024",
                protocol_revision: 2,
                protocol_sha256: "deadbeef",
                is_synthetic_fixture: false,
              },
              target_comparisons: [
                {
                  condition_id: "sugar_grn_100hz",
                  neuron_id: "720575940660219265",
                  label: "MN9_right",
                  n_replicates: 30,
                  observed_mean_hz: 68.833,
                  observed_sd_pop_hz: 4.243,
                  reference_mean_hz: 67.033,
                  reference_sd_pop_hz: 6.595,
                  abs_diff_from_ref_hz: 1.8,
                  tolerance_abs_hz: 5.0,
                  passed: true,
                },
              ],
              contrast_comparisons: [],
            },
          },
        ],
      });
    }
    if (target.endsWith("/api/v1/analyses")) {
      return mockJsonResponse({ analyses: [] });
    }
    if (target.endsWith("/api/v1/exports")) {
      return mockJsonResponse({ exports: [] });
    }
    if (target.endsWith("/api/v1/audit?limit=30")) {
      return mockJsonResponse({ events: [] });
    }
    return mockJsonResponse({});
  });
}

function installMemoryStorage(): Storage {
  const store = new Map<string, string>();
  const mockStorage: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key: string) => store.get(key) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(key);
    },
    setItem: (key: string, value: string) => {
      store.set(key, String(value));
    },
  };
  Object.defineProperty(window, "localStorage", {
    value: mockStorage,
    configurable: true,
    writable: true,
  });
  return mockStorage;
}

describe("SYNAPSE Research Workbench UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    installMemoryStorage();
  });

  it("preserves 64-bit string neuron IDs, renders RUO/synthetic badges, enforces freeze confirm, and cancels jobs", async () => {
    const fetchMock = createApiFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(
      <LanguageProvider>
        <App />
      </LanguageProvider>,
    );

    expect((await screen.findAllByText("RESEARCH USE ONLY (RUO)")).length).toBeGreaterThanOrEqual(
      1,
    );

    // Modules tab: real Pain, Metabolic, and Planned modules
    fireEvent.click(screen.getByRole("tab", { name: /Research Modules/ }));
    expect(await screen.findByText("120 / 120")).toBeInTheDocument();
    expect(screen.getByText("+20.667")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Metabolic · P4-MET-001/ }));
    expect(await screen.findByText("+30.900")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Planned Modules/ }));
    expect(screen.getByText(/Sleep & Circadian Regulation/)).toBeInTheDocument();

    // Datasets & Circuits tab: 64-bit integer precision preserved as string + 3D/2D view toggle
    fireEvent.click(screen.getByRole("tab", { name: /Datasets & Circuits/ }));
    expect(screen.getByRole("button", { name: "3D WebGL (Three.js)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2D SVG" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load Neurons" }));
    expect(await screen.findByText("9007199254740996")).toBeInTheDocument();
    expect(screen.getByText("SYNTHETIC FIXTURE — NOT BIOLOGICAL DATA")).toBeInTheDocument();

    // Models & Protocols tab: freeze button remains disabled until confirmation checkbox checked
    fireEvent.click(screen.getByRole("tab", { name: /Models & Protocols/ }));
    const freezeBtn = screen.getByRole("button", { name: "Freeze Protocol Revision" });
    expect(freezeBtn).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Validate Draft YAML" }));
    expect(await screen.findByText(/DRAFT-TEST-001/)).toBeInTheDocument();
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(freezeBtn).toBeEnabled();
    fireEvent.click(freezeBtn);
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/protocols/freeze"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /Inspect YAML/ }));
    expect(await screen.findByText(/protocol_id: P0-SYNTH-001/)).toBeInTheDocument();

    // Jobs & Runs tab: job cancellation action
    fireEvent.click(screen.getByRole("tab", { name: /Jobs & Runs/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs/job_running123/cancel"),
        expect.objectContaining({ method: "POST" }),
      ),
    );

    // Results & Exports tab: exact 64-bit string ID preserved in benchmark table
    fireEvent.click(screen.getByRole("tab", { name: /Results & Exports/ }));
    expect(await screen.findByText("720575940660219265")).toBeInTheDocument();
  });

  it("supports live Turkish/English switching with localStorage persistence and dark/light theme toggling", async () => {
    const fetchMock = createApiFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(
      <LanguageProvider>
        <App />
      </LanguageProvider>,
    );

    expect((await screen.findAllByText("RESEARCH USE ONLY (RUO)")).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(document.documentElement.dataset.theme).toBe("dark");

    // Switch to Turkish
    fireEvent.click(screen.getByRole("button", { name: "TR" }));
    expect(
      (await screen.findAllByText("YALNIZCA ARAŞTIRMA AMAÇLIDIR (RUO)")).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("tab", { name: /Araştırma Modülleri/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Veri Setleri ve Devreler/ })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("tr");
    expect(window.localStorage.getItem("synapse.lang")).toBe("tr");

    // Verify Turkish 3D & 2D labels on Datasets & Circuits tab
    fireEvent.click(screen.getByRole("tab", { name: /Veri Setleri ve Devreler/ }));
    expect(screen.getByRole("button", { name: "3B WebGL (Three.js)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2B SVG" })).toBeInTheDocument();

    // Toggle theme to Light Ivory
    fireEvent.click(screen.getByRole("button", { name: /Açık Fildişi temasına geç/ }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("synapse.theme")).toBe("light");

    // Switch back to English
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    expect((await screen.findAllByText("RESEARCH USE ONLY (RUO)")).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(document.documentElement.lang).toBe("en");
  });
});
