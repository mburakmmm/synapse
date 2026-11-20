import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";

function mockJsonResponse(payload: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(payload),
  } as Response);
}

describe("SYNAPSE Research Workbench UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("preserves 64-bit string neuron IDs, renders RUO/synthetic badges, enforces freeze confirm, and cancels jobs", async () => {
    const fetchMock = vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
      const target = String(url);
      if (target.endsWith("/api/v1/health")) {
        return mockJsonResponse({
          status: "ok",
          api_version: "v1",
          ruo_notice: "Research Use Only",
          bind_host: "127.0.0.1",
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
      if (target.endsWith("/api/v1/runs?limit=50")) {
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

    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByText("RESEARCH USE ONLY (RUO)")).toBeInTheDocument();

    // Tab 2: 64-bit integer precision preserved as string ("9007199254740996" > Number.MAX_SAFE_INTEGER)
    fireEvent.click(screen.getByRole("tab", { name: "Datasets & Circuits" }));
    fireEvent.click(screen.getByRole("button", { name: "Load Neurons" }));
    expect(await screen.findByText("9007199254740996")).toBeInTheDocument();
    expect(screen.getByText("SYNTHETIC FIXTURE — NOT BIOLOGICAL DATA")).toBeInTheDocument();

    // Tab 3: freeze button remains disabled until explicit human confirmation checkbox is checked
    fireEvent.click(screen.getByRole("tab", { name: "Models & Protocols" }));
    const freezeBtn = screen.getByRole("button", { name: "Freeze Protocol Revision" });
    expect(freezeBtn).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(freezeBtn).toBeEnabled();
    fireEvent.click(freezeBtn);
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/protocols/freeze"),
        expect.objectContaining({ method: "POST" }),
      ),
    );

    // Tab 4: job cancellation action
    fireEvent.click(screen.getByRole("tab", { name: "Jobs & Runs" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs/job_running123/cancel"),
        expect.objectContaining({ method: "POST" }),
      ),
    );

    // Tab 5: exact 64-bit string ID preserved in benchmark table
    fireEvent.click(screen.getByRole("tab", { name: "Results & Exports" }));
    expect(await screen.findByText("720575940660219265")).toBeInTheDocument();
  });
});
