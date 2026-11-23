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
        storage: {
          data_dir_exists: true,
          runs_dir_exists: true,
          disk_free_gb: 128.5,
          disk_total_gb: 512.0,
        },
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
            ui_state: "experimental",
            simulation_phase: "l3_verified_and_l1_pilot_complete",
            dataset_id: "malecns_v1_0",
            protocol_id: "P5-SLEEP-001-PILOT",
            available_on_disk: true,
          },
          {
            module_id: "addiction",
            phase: "phase5b",
            ui_state: "experimental",
            simulation_phase: "l2_verified_and_l1_pilot_complete",
            dataset_id: "malecns_v1_0",
            protocol_id: "P5-ADD-001-PILOT",
            available_on_disk: true,
          },
          {
            module_id: "neuro",
            phase: "phase5c",
            ui_state: "planned",
            simulation_phase: "planned",
            dataset_id: null,
            protocol_id: null,
            available_on_disk: false,
          },
          {
            module_id: "pharma",
            phase: "phase5c",
            ui_state: "planned",
            simulation_phase: "planned",
            dataset_id: null,
            protocol_id: null,
            available_on_disk: false,
          },
          {
            module_id: "stress",
            phase: "phase5c",
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
        sleep: {
          l3_gate: {
            model_id: "leloup_goldbeter_1998_two_process_v1",
            model_level: "L3",
            parameter_manifest_sha256: "l3sha",
            overall_passed: true,
            gates: {
              dd_free_running_and_convergence: {
                passed: true,
                tau_dd_coarse_h: 24.1346,
                tau_dd_sd_h: 1e-5,
                tau_dd_fine_h: 24.1346,
                convergence_abs_diff_h: 0.0,
              },
              ld12_12_entrainment: {
                passed: true,
                tau_ld_h: 24.0171,
                zt_peak_mean_h: 21.4539,
                zt_peak_sd_h: 0.0295,
              },
              light_pulse_prc: {
                passed: true,
                max_abs_daytime_dead_zone_h: 0.0035,
                max_early_night_delay_h: -2.3591,
                late_night_ct21_advance_h: 2.3431,
                curve: [
                  {
                    ct_hours: 15,
                    pulse_start_h: 39.08,
                    pulse_end_h: 41.08,
                    phase_shift_h: -2.3591,
                    direction: "delay",
                  },
                  {
                    ct_hours: 21,
                    pulse_start_h: 45.12,
                    pulse_end_h: 47.12,
                    phase_shift_h: 2.3431,
                    direction: "advance",
                  },
                ],
              },
              homeostatic_deprivation_rebound: {
                passed: true,
                baseline_s_peak: 0.7425,
                deprivation_s_peak: 0.9283,
                baseline_24h_recovery_rest_fraction: 0.5021,
                deprivation_24h_recovery_rest_fraction: 0.6646,
                recovery_rest_fraction_delta: 0.1625,
                day9_washout_rest_fraction_delta: -0.0042,
              },
            },
          },
          l3_shift_work: {
            model_id: "leloup_goldbeter_1998_two_process_v1",
            parameter_manifest_sha256: "l3sha",
            gate_overall_passed: true,
            arms: {
              rotating_shift_8h: {
                arm_id: "rotating_shift_8h",
                duration_h: 384,
                s_peak_overall: 0.7419,
                s_mean_post_onset: 0.5116,
                modeled_rest_fraction_post_onset: 0.4991,
                max_abs_phase_error_h: 10.814,
                days_to_reentrain: null,
              },
            },
          },
          pilot: {
            protocol_id: "P5-SLEEP-001-PILOT",
            dataset_id: "malecns_v1_0",
            total_runs: 24,
            succeeded_run_count: 24,
            failed_run_count: 0,
            sham_count: 3,
            sham_max_spikes: 0,
            wall_total_s: 4700.87,
            run_wall_mean_s: 195.87,
            git_commits: ["b752e87"],
            cohort_stim_mean_hz: {
              tutub_b_interneuron: { light_day_baseline: 160.33, light_plus_clock_dn1p_drive: 141.67 },
              tubu01_relay: { light_day_baseline: 2.07, shift_light_misaligned_clock_debt: 9.87 },
              exr1_helicon: { light_day_baseline: 0.0, shift_light_misaligned_clock_debt: 3.83 },
              er5_sleep_homeostat: { light_day_baseline: 0.0, shift_light_misaligned_clock_debt: 2.83 },
            },
            contrasts: [
              {
                contrast_name: "analysis_22794_clock_vs_base",
                neuron_id: "22794",
                baseline_condition: "light_day_baseline",
                treatment_condition: "light_plus_clock_dn1p_drive",
                n_pairs: 3,
                failed_run_count: 0,
                baseline_mean_hz: 102.083,
                baseline_sd_hz: 2.602,
                treatment_mean_hz: 89.167,
                treatment_sd_hz: 2.602,
                mean_difference_hz: -12.917,
                sd_difference_hz: 4.507,
                bootstrap_ci95_low_hz: -18.75,
                bootstrap_ci95_high_hz: -8.75,
              },
            ],
          },
        },
        addiction: {
          l2_gate: {
            model_id: "mb_dopamine_plasticity_v1",
            model_level: "L2",
            parameter_manifest_sha256: "l2sha",
            overall_passed: true,
            gates: {
              numerical_convergence_and_bounds: {
                passed: true,
                dt_coarse_s: 0.05,
                dt_fine_s: 0.025,
                weights_within_bounds: true,
                max_abs_weight_diff: 0.00019469,
                max_abs_pi_diff: 0.00007855,
              },
              acquisition_specificity: {
                passed: true,
                pi_acq: 0.33123,
                w_avoid_cs_plus_acq: 0.292978,
                w_avoid_cs_minus_abs_err: 0.0,
                v_cs_minus_abs_err: 0.0,
              },
              parallel_memory_extinction: {
                passed: true,
                pi_ext: 0.045171,
                pi_drop_acq_to_ext: 0.286059,
                w_appr_cs_plus_ext: 0.384344,
                w_avoid_cs_plus_ext: 0.334152,
              },
              reinstatement_recovery: {
                passed: true,
                pi_reinst: 0.2658,
                pi_gain_ext_to_reinst: 0.220629,
                w_appr_cs_plus_reinst: 0.924609,
                w_avoid_cs_minus_abs_err: 0.0,
              },
              negative_controls_null: {
                passed: true,
                sham_max_abs_pi: 0.0,
                sham_max_weight_dev: 0.0,
                yoked_unpaired_acq_pi: 0.000062,
                dan_blocked_max_abs_pi: 0.0,
              },
            },
          },
          l2_paradigm: {
            model_id: "mb_dopamine_plasticity_v1",
            parameter_manifest_sha256: "l2sha",
            gate_overall_passed: true,
            arms: {
              paired_conditioning: {
                arm_id: "paired_conditioning",
                duration_s: 310,
                max_abs_pi_proxy: 0.36459,
                phase_snapshots: {
                  naive: {
                    time_s: 10,
                    pi_proxy: 0.0,
                    v_cs_plus: -0.142857,
                    v_cs_minus: -0.142857,
                    w_avoid_cs_plus: 1.0,
                    w_avoid_cs_minus: 1.0,
                    w_appr_cs_plus: 1.0,
                    w_appr_cs_minus: 1.0,
                  },
                  acquisition: {
                    time_s: 145,
                    pi_proxy: 0.33123,
                    v_cs_plus: 0.519604,
                    v_cs_minus: -0.142857,
                    w_avoid_cs_plus: 0.292978,
                    w_avoid_cs_minus: 1.0,
                    w_appr_cs_plus: 1.0,
                    w_appr_cs_minus: 1.0,
                  },
                  extinction: {
                    time_s: 235,
                    pi_proxy: 0.045171,
                    v_cs_plus: -0.052515,
                    v_cs_minus: -0.142858,
                    w_avoid_cs_plus: 0.334152,
                    w_avoid_cs_minus: 1.0,
                    w_appr_cs_plus: 0.384344,
                    w_appr_cs_minus: 0.9999993,
                  },
                  reinstatement: {
                    time_s: 310,
                    pi_proxy: 0.2658,
                    v_cs_plus: 0.388743,
                    v_cs_minus: -0.142857,
                    w_avoid_cs_plus: 0.366625,
                    w_avoid_cs_minus: 1.0,
                    w_appr_cs_plus: 0.924609,
                    w_appr_cs_minus: 1.0,
                  },
                },
              },
            },
            l2_to_l1_weight_snapshots: [],
          },
          pilot: {
            protocol_id: "P5-ADD-001-PILOT",
            dataset_id: "malecns_v1_0",
            total_runs: 24,
            succeeded_run_count: 24,
            failed_run_count: 0,
            sham_count: 3,
            sham_max_spikes: 0,
            wall_total_s: 1850.0,
            run_wall_mean_s: 77.08,
            git_commits: ["3af2151"],
            cohort_stim_mean_hz: {
              mbon02_avoid: { cs_plus_naive_baseline: 22.0, cs_plus_post_acquisition: 0.0 },
              mbon14_appr: { cs_plus_naive_baseline: 22.0, cs_plus_post_acquisition: 28.0 },
              mbon18_appr: { cs_plus_post_extinction: 0.0, cs_plus_post_reinstatement: 40.0 },
              mbon12_appr: { cs_plus_naive_baseline: 22.0, cs_plus_post_acquisition: 28.0 },
            },
            contrasts: [
              {
                contrast_name: "analysis_522444_acq_vs_naive",
                neuron_id: "522444",
                baseline_condition: "cs_plus_naive_baseline",
                treatment_condition: "cs_plus_post_acquisition",
                n_pairs: 3,
                failed_run_count: 0,
                baseline_mean_hz: 31.667,
                baseline_sd_hz: 1.667,
                treatment_mean_hz: 0.0,
                treatment_sd_hz: 0.0,
                mean_difference_hz: -31.667,
                sd_difference_hz: 1.667,
                bootstrap_ci95_low_hz: -33.333,
                bootstrap_ci95_high_hz: -30.0,
              },
            ],
          },
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
            confidence: 0.98,
          },
        ],
      });
    }
    if (target.endsWith("/subgraph")) {
      return mockJsonResponse({
        metadata: {
          source_dataset_id: "synthetic_microcircuit_v1",
          source_graph_sha256: "abc123",
          subgraph_sha256: "sub123",
          seed_neuron_ids: ["9007199254740993"],
          hop_limit: 2,
          direction: "outgoing",
          n_selected_neurons: 2,
          n_selected_edges: 1,
          omitted_incoming_edge_count: 0,
          omitted_outgoing_edge_count: 0,
          omitted_incoming_synapse_count: 0,
          omitted_outgoing_synapse_count: 0,
          isolation_limitations: ["Boundary omitted"],
        },
        nodes: [
          {
            source_neuron_id: "9007199254740993",
            neurotransmitter: "ACH",
            is_seed: true,
            cell_type: "SEED_IN",
          },
          {
            source_neuron_id: "9007199254740996",
            neurotransmitter: "GABA",
            is_seed: false,
            cell_type: "TEST_OUTPUT",
          },
        ],
        edges: [
          {
            pre_neuron_id: "9007199254740993",
            post_neuron_id: "9007199254740996",
            synapse_count: 12,
          },
        ],
        edges_truncated: false,
      });
    }
    if (target.endsWith("/api/v1/models")) {
      return mockJsonResponse({
        models: [
          {
            model_id: "shiu2024_lif",
            model_revision: "1.0",
            model_level: "L1",
            parameter_manifest_sha256: "abc",
            solver: "linear",
            dt_s: 0.0001,
            dg_unless_refractory: true,
            parameter_source: "Shiu 2024",
            parameters: { v_rest_v: -0.052, w_syn_v: 0.000275 },
          },
          {
            model_id: "mb_dopamine_plasticity_v1",
            model_revision: "1.0",
            model_level: "L2",
            parameter_manifest_sha256: "l2sha",
            solver: "rk4",
            dt_s: 0.05,
            parameter_source: "Aso 2014 / Felsenberg 2018",
            parameters: { tau_e_s: 4.0, eta_ltd_pam: 0.09 },
          },
          {
            model_id: "leloup_goldbeter_1998_two_process_v1",
            model_revision: "1.0",
            model_level: "L3",
            parameter_manifest_sha256: "l3sha",
            solver: "RK45",
            dt_s: 180.0,
            parameter_source: "Leloup & Goldbeter 1998",
            parameters: { tau_i_h: 8.76, tau_d_h: 9.51 },
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
      return mockJsonResponse({
        analyses: [
          {
            analysis_key: "analysis_arm_1",
            relative_dir: "arm1",
            target_neuron_id: "720575940660219265",
            baseline_condition: "base",
            treatment_condition: "treat1",
            failed_run_count: 0,
            provenance: {
              dataset_id: "flywire_fafb_v630",
              model_id: "shiu2024_lif",
              protocol_id: "P4-MET-001",
              protocol_sha256: "aaa",
              is_synthetic_fixture: false,
            },
            paired_metrics: {
              n_pairs: 30,
              mean_difference_hz: 22.0,
              sd_difference_hz: 7.7,
              bootstrap_ci95_low_hz: 19.2,
              bootstrap_ci95_high_hz: 24.7,
              uncertainty_interpretation: "conditional",
              permutation_test: { method: "monte_carlo_sign_flip", two_sided_p_value: 9.999e-5 },
            },
          },
          {
            analysis_key: "analysis_arm_2",
            relative_dir: "arm2",
            target_neuron_id: "720575940660219265",
            baseline_condition: "base",
            treatment_condition: "treat2",
            failed_run_count: 0,
            provenance: {
              dataset_id: "flywire_fafb_v630",
              model_id: "shiu2024_lif",
              protocol_id: "P4-MET-001",
              protocol_sha256: "bbb",
              is_synthetic_fixture: false,
            },
            paired_metrics: {
              n_pairs: 30,
              mean_difference_hz: 30.9,
              sd_difference_hz: 7.1,
              bootstrap_ci95_low_hz: 28.2,
              bootstrap_ci95_high_hz: 33.4,
              uncertainty_interpretation: "conditional",
              permutation_test: { method: "monte_carlo_sign_flip", two_sided_p_value: 9.999e-5 },
            },
          },
        ],
      });
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

  it("opens in Simple Mode by default, then switches to Expert Mode and preserves all scientific safety invariants", async () => {
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

    // Default startup is Simple Mode with 4 friendly tabs + plain glossary
    expect(screen.getByText("Understand Connectome Simulations Without Jargon")).toBeInTheDocument();
    expect(screen.getByText("Plain-Language Scientific Glossary")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /3D Brain Circuit/ })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /Models & Protocols/ })).not.toBeInTheDocument();

    // Switch to Expert Mode
    fireEvent.click(screen.getAllByRole("button", { name: "Expert" })[0]);
    expect(window.localStorage.getItem("synapse.uiMode")).toBe("expert");
    expect(await screen.findByText(/128\.5 \/ 512 GB/)).toBeInTheDocument();

    // Modules tab: real Addiction, Sleep, Pain, Metabolic, and Planned modules
    fireEvent.click(screen.getByRole("tab", { name: /Research Modules/ }));
    expect(await screen.findByText("120 / 120")).toBeInTheDocument();
    expect(screen.getByText("+20.667")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Addiction · P5-ADD-001/ }));
    expect(await screen.findByText(/\+0\.331 PI/)).toBeInTheDocument();
    expect(screen.getByText("-31.667")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Sleep · P5-SLEEP-001/ }));
    expect(await screen.findByText(/24\.13/)).toBeInTheDocument();
    expect(screen.getByText("-12.917")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Metabolic · P4-MET-001/ }));
    expect(await screen.findByText("+30.900")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Planned Modules/ }));
    expect(screen.getByText(/Neurodegeneration & Resilience/)).toBeInTheDocument();

    // Datasets & Circuits tab: 64-bit string ID + confidence column + 3D/2D controls
    fireEvent.click(screen.getByRole("tab", { name: /Datasets & Circuits/ }));
    expect(screen.getByRole("button", { name: "3D WebGL (Three.js)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2D SVG" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load Neurons" }));
    expect(await screen.findByText("9007199254740996")).toBeInTheDocument();
    expect(screen.getByText("0.98")).toBeInTheDocument();
    expect(screen.getByText("SYNTHETIC FIXTURE — NOT BIOLOGICAL DATA")).toBeInTheDocument();

    // Models & Protocols tab: Quick Form -> Draft YAML Builder + L2/L3 badges + Validate + disabled freeze button
    fireEvent.click(screen.getByRole("tab", { name: /Models & Protocols/ }));
    expect(screen.getByText(/L2 Plasticity · solver: rk4/)).toBeInTheDocument();
    expect(screen.getByText(/L3 ODE · solver: RK45/)).toBeInTheDocument();
    expect(screen.queryByText(/dg=undefined/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate Draft YAML" }));
    fireEvent.click(screen.getByRole("button", { name: "Validate Draft YAML" }));
    expect(await screen.findByText(/DRAFT-TEST-001/)).toBeInTheDocument();

    const freezeBtn = screen.getByRole("button", { name: "Freeze Protocol Revision" });
    expect(freezeBtn).toBeDisabled();
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

    // Jobs & Runs tab: Auto-Refresh + pagination + job cancel
    fireEvent.click(screen.getByRole("tab", { name: /Jobs & Runs/ }));
    expect(screen.getByRole("button", { name: "Auto-Refresh (5s)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prev 50" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next 50" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/jobs/job_running123/cancel"),
        expect.objectContaining({ method: "POST" }),
      ),
    );

    // Results & Exports tab: 64-bit string ID + Side-by-Side Analysis Comparison
    fireEvent.click(screen.getByRole("tab", { name: /Results & Exports/ }));
    expect((await screen.findAllByText("720575940660219265")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Side-by-Side Analysis Comparison")).toBeInTheDocument();
  });

  it("supports live Turkish/English switching in Simple & Expert modes plus dark/light themes", async () => {
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

    // Switch to Turkish while in Simple Mode
    fireEvent.click(screen.getByRole("button", { name: "TR" }));
    expect(
      (await screen.findAllByText("YALNIZCA ARAŞTIRMA AMAÇLIDIR (RUO)")).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("tab", { name: /Başlangıç/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Deney Özetleri/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /3B Beyin Devresi/ })).toBeInTheDocument();
    expect(screen.getByText("Uyku ve Biyolojik Saat Hikayesi (L3 + Erkek Beyin)")).toBeInTheDocument();
    expect(screen.getByText("Ödül Öğrenmesi ve Sönme Hikayesi (L2 + Erkek MB)")).toBeInTheDocument();
    expect(screen.getByText("Sade Bilimsel Terimler Sözlüğü")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sirkadiyen Saat/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sinaptik Plastisite/ })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("tr");
    expect(window.localStorage.getItem("synapse.lang")).toBe("tr");

    // Open 3B Beyin Devresi in Simple Mode and confirm auto-loaded 3D controls
    fireEvent.click(screen.getByRole("tab", { name: /3B Beyin Devresi/ }));
    expect(await screen.findByRole("button", { name: "3B WebGL (Three.js)" })).toBeInTheDocument();
    expect(screen.getByText(/Hızlı 3B Renk Rehberi/)).toBeInTheDocument();

    // Switch to Uzman Modu in Turkish
    fireEvent.click(screen.getByRole("button", { name: "Uzman Modu" }));
    expect(window.localStorage.getItem("synapse.uiMode")).toBe("expert");
    expect(screen.getByRole("tab", { name: /Modeller ve Protokoller/ })).toBeInTheDocument();

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
