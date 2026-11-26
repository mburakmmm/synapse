import React, { useMemo, useState } from "react";
import type { PlotlyTrace } from "plotly.js-basic-dist-min";
import type { BenchmarkEnvelope, StudiesResponse } from "../api";
import type { UiMode } from "../App";
import { PlotlyChart } from "../components/PlotlyChart";
import { StatusBadge } from "../components/StatusBadge";
import { useI18n } from "../i18n/LanguageContext";

import type { CircuitPresetRequest } from "./DatasetsView";

export type ModuleSectionTab =
  | "stress"
  | "pharma"
  | "neuro"
  | "addiction"
  | "sleep"
  | "pain"
  | "metabolic"
  | "benchmark"
  | "planned";

const STRESS_CONDITIONS_ORDER = [
  "sham_zero_stimulus",
  "acute_threat_baseline_30hz",
  "acute_threat_high_60hz",
  "chronic_allostatic_reserve_drop",
  "chronic_allostatic_reserve_depletion",
  "chronic_arousal_sensory_sensitization",
  "matched_ctrl_nondefensive_visual_60hz",
  "matched_ctrl_offpathway_inh_depletion",
];

const STRESS_COND_SHORT: Record<string, string> = {
  sham_zero_stimulus: "Sham 0",
  acute_threat_baseline_30hz: "Acute 30Hz",
  acute_threat_high_60hz: "Acute 60Hz",
  chronic_allostatic_reserve_drop: "Reserve 0.5x",
  chronic_allostatic_reserve_depletion: "Reserve 0.0x",
  chronic_arousal_sensory_sensitization: "Sensitized",
  matched_ctrl_nondefensive_visual_60hz: "Ctrl Visual",
  matched_ctrl_offpathway_inh_depletion: "Ctrl Off-Inh",
};

const PHARMA_CONDITIONS_ORDER = [
  "sham_zero_stimulus",
  "vehicle_baseline_40hz",
  "rdl_gaba_antag_50pct",
  "rdl_gaba_antag_100pct",
  "rdl_gaba_pam_175pct",
  "nachr_ach_atten_50pct",
  "combined_rdl_pam_plus_nachr_atten",
  "matched_ctrl_rdl_antag_100pct",
];

const PHARMA_COND_SHORT: Record<string, string> = {
  sham_zero_stimulus: "Sham 0",
  vehicle_baseline_40hz: "Vehicle 40Hz",
  rdl_gaba_antag_50pct: "Rdl Antag 50%",
  rdl_gaba_antag_100pct: "Rdl Block 100%",
  rdl_gaba_pam_175pct: "Rdl PAM 1.75x",
  nachr_ach_atten_50pct: "nAChR 50%",
  combined_rdl_pam_plus_nachr_atten: "PAM + nAChR",
  matched_ctrl_rdl_antag_100pct: "Ctrl Rdl 100%",
};

const NEURO_CONDITIONS_ORDER = [
  "sham_zero_stimulus",
  "intact_baseline_100hz",
  "matched_random_cell_loss_12",
  "matched_random_synapse_loss",
  "targeted_synapse_loss_50pct",
  "targeted_synapse_loss_100pct",
  "targeted_cell_loss_top6",
  "targeted_cell_loss_top12",
];

const NEURO_COND_SHORT: Record<string, string> = {
  sham_zero_stimulus: "Sham 0",
  intact_baseline_100hz: "Intact 100Hz",
  matched_random_cell_loss_12: "Ctrl Cells (12)",
  matched_random_synapse_loss: "Ctrl Syn (24e)",
  targeted_synapse_loss_50pct: "Hub Syn 50%",
  targeted_synapse_loss_100pct: "Hub Syn 100%",
  targeted_cell_loss_top6: "Hub Cells (6)",
  targeted_cell_loss_top12: "Hub Cells (12)",
};

const ADDICTION_CONDITIONS_ORDER = [
  "sham_zero_stimulus",
  "cs_plus_naive_baseline",
  "cs_plus_post_acquisition",
  "cs_plus_post_extinction",
  "cs_plus_post_reinstatement",
  "cs_plus_yoked_matched_ctrl",
  "cs_minus_naive_baseline",
  "cs_minus_after_cs_plus_acq",
];

const ADDICTION_COND_SHORT: Record<string, string> = {
  sham_zero_stimulus: "Sham 0",
  cs_plus_naive_baseline: "CS+ Naive",
  cs_plus_post_acquisition: "CS+ Acq",
  cs_plus_post_extinction: "CS+ Ext",
  cs_plus_post_reinstatement: "CS+ Reinst",
  cs_plus_yoked_matched_ctrl: "Yoked Ctrl",
  cs_minus_naive_baseline: "CS- Naive",
  cs_minus_after_cs_plus_acq: "CS- After Acq",
};

const SLEEP_CONDITIONS_ORDER = [
  "sham_zero_stimulus",
  "light_day_baseline",
  "light_plus_clock_dn1p_drive",
  "light_plus_matched_ctrl_clock_drive",
  "light_plus_dn1p_avp_edge_mask",
  "light_plus_er5_high_homeostat_gain",
  "light_plus_er5_exr1_edge_mask",
  "shift_light_misaligned_clock_debt",
];

const SLEEP_COND_SHORT: Record<string, string> = {
  sham_zero_stimulus: "Sham 0",
  light_day_baseline: "Day Base",
  light_plus_clock_dn1p_drive: "+DN1p Clock",
  light_plus_matched_ctrl_clock_drive: "+Matched Ctrl",
  light_plus_dn1p_avp_edge_mask: "DN1p->AVP Mask",
  light_plus_er5_high_homeostat_gain: "ER5 Gain 1.5x",
  light_plus_er5_exr1_edge_mask: "ER5->ExR1 Mask",
  shift_light_misaligned_clock_debt: "50Hz Shift+Debt",
};

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
  const sleepL3Gate = studies?.sleep?.l3_gate ?? null;
  const sleepShift = studies?.sleep?.l3_shift_work ?? null;
  const sleepPilot = studies?.sleep?.pilot ?? null;
  const addL2Gate = studies?.addiction?.l2_gate ?? null;
  const addL2Paradigm = studies?.addiction?.l2_paradigm ?? null;
  const addPilot = studies?.addiction?.pilot ?? null;
  const neuroL0Gate = studies?.neuro?.l0_gate ?? null;
  const neuroL0Summary = studies?.neuro?.l0_summary ?? null;
  const neuroMalecns = studies?.neuro?.malecns_l0_audit ?? null;
  const neuroPilot = studies?.neuro?.pilot ?? null;
  const pharmaL2Gate = studies?.pharma?.l2_gate ?? null;
  const pharmaL2Panel = studies?.pharma?.l2_panel ?? null;
  const pharmaPilot = studies?.pharma?.pilot ?? null;
  const stressL3Gate = studies?.stress?.l3_gate ?? null;
  const stressL3Panel = studies?.stress?.l3_panel ?? null;
  const stressPilot = studies?.stress?.pilot ?? null;
  const metConf = studies?.metabolic.confirmatory ?? [];
  const metRob = studies?.metabolic.robustness ?? {};

  const stressL3TrajTraces = useMemo<PlotlyTrace[]>(() => {
    const trajs = stressL3Panel?.trajectories;
    if (!trajs) return [];
    const traces: PlotlyTrace[] = [];
    const specs: Array<{ arm: string; label: string; color: string }> = [
      { arm: "acute_single_threat", label: "Acute", color: "#0072B2" },
      { arm: "chronic_repeated_stress", label: "Chronic Repeat", color: "#D55E00" },
      { arm: "chronic_with_washout_recovery", label: "Chronic + Washout", color: "#009E73" },
    ];
    for (const sp of specs) {
      const pts = trajs[sp.arm] ?? [];
      if (pts.length === 0) continue;
      traces.push({
        type: "scatter",
        mode: "lines",
        name: `${sp.label} Reserve C`,
        x: pts.map((p) => p.time_h),
        y: pts.map((p) => p.reserve_c),
        line: { color: sp.color, width: 2.3 },
      });
      traces.push({
        type: "scatter",
        mode: "lines",
        name: `${sp.label} Load L`,
        x: pts.map((p) => p.time_h),
        y: pts.map((p) => p.load_l),
        line: { color: sp.color, width: 1.8, dash: "dot" },
      });
    }
    return traces;
  }, [stressL3Panel]);

  const stressL1ReadoutTraces = useMemo<PlotlyTrace[]>(() => {
    const condMap = stressPilot?.condition_readout_means;
    if (!condMap) return [];
    const xLabels = STRESS_CONDITIONS_ORDER.map((c) => STRESS_COND_SHORT[c] ?? c);
    return [
      {
        type: "bar",
        name: "DNp01 Escape (Hz)",
        x: xLabels,
        y: STRESS_CONDITIONS_ORDER.map((c) => condMap[c]?.dnp01_escape_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: STRESS_CONDITIONS_ORDER.map((c) => condMap[c]?.dnp01_escape_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#D55E00" },
      },
      {
        type: "bar",
        name: "DNp09 Freeze (Hz)",
        x: xLabels,
        y: STRESS_CONDITIONS_ORDER.map((c) => condMap[c]?.dnp09_freeze_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: STRESS_CONDITIONS_ORDER.map((c) => condMap[c]?.dnp09_freeze_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#0072B2" },
      },
      {
        type: "bar",
        name: "DNp11 Escape (Hz)",
        x: xLabels,
        y: STRESS_CONDITIONS_ORDER.map((c) => condMap[c]?.dnp11_escape_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: STRESS_CONDITIONS_ORDER.map((c) => condMap[c]?.dnp11_escape_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#009E73" },
      },
    ];
  }, [stressPilot]);

  const pharmaL2CurveTraces = useMemo<PlotlyTrace[]>(() => {
    if (!pharmaL2Panel) return [];
    const rdlAntag = pharmaL2Panel.rdl_gaba_a_noncomp_curve;
    const rdlPam = pharmaL2Panel.rdl_gaba_a_pam_curve;
    const achNoncomp = pharmaL2Panel.nachr_ach_noncomp_curve;
    return [
      {
        type: "scatter",
        mode: "lines",
        name: "Rdl (GABA_A) Antagonist Scale",
        x: rdlAntag.map((p) => p.log10_ratio),
        y: rdlAntag.map((p) => p.conductance_scale),
        line: { color: "#D55E00", width: 2.5 },
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Rdl (GABA_A) PAM Gain",
        x: rdlPam.map((p) => p.log10_ratio),
        y: rdlPam.map((p) => p.conductance_scale),
        line: { color: "#009E73", width: 2.5 },
      },
      {
        type: "scatter",
        mode: "lines",
        name: "nAChR (ACH) Attenuation Scale",
        x: achNoncomp.map((p) => p.log10_ratio),
        y: achNoncomp.map((p) => p.conductance_scale),
        line: { color: "#0072B2", width: 2, dash: "dash" },
      },
    ];
  }, [pharmaL2Panel]);

  const pharmaL1ReadoutTraces = useMemo<PlotlyTrace[]>(() => {
    const condMap = pharmaPilot?.condition_readout_means;
    if (!condMap) return [];
    const xLabels = PHARMA_CONDITIONS_ORDER.map((c) => PHARMA_COND_SHORT[c] ?? c);
    return [
      {
        type: "bar",
        name: "523539 (ANXXX027_L)",
        x: xLabels,
        y: PHARMA_CONDITIONS_ORDER.map((c) => condMap[c]?.anxxx027_l_523539_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: PHARMA_CONDITIONS_ORDER.map((c) => condMap[c]?.anxxx027_l_523539_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#D55E00" },
      },
      {
        type: "bar",
        name: "558778 (AN08B012_R)",
        x: xLabels,
        y: PHARMA_CONDITIONS_ORDER.map((c) => condMap[c]?.an08b012_r_558778_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: PHARMA_CONDITIONS_ORDER.map((c) => condMap[c]?.an08b012_r_558778_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#0072B2" },
      },
      {
        type: "bar",
        name: "10592 (AN08B012_L)",
        x: xLabels,
        y: PHARMA_CONDITIONS_ORDER.map((c) => condMap[c]?.an08b012_l_10592_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: PHARMA_CONDITIONS_ORDER.map((c) => condMap[c]?.an08b012_l_10592_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#009E73" },
      },
    ];
  }, [pharmaPilot]);

  const neuroL0CurveTraces = useMemo<PlotlyTrace[]>(() => {
    const pts = neuroL0Summary?.curve_points ?? [];
    if (pts.length === 0) return [];
    const tgt = pts
      .filter((p) => p.arm_type === "targeted_cell_loss")
      .sort((a, b) => a.step_k - b.step_k);
    const ctrl = pts
      .filter((p) => p.arm_type === "matched_random_cell_loss")
      .sort((a, b) => a.step_k - b.step_k);
    return [
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Targeted Hub Efficiency Ratio",
        x: tgt.map((p) => p.step_k),
        y: tgt.map((p) => p.weighted_eff_ratio),
        line: { color: "#D55E00", width: 2.5 },
        marker: { size: 7, color: "#D55E00" },
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Matched-Ctrl Efficiency Ratio",
        x: ctrl.map((p) => p.step_k),
        y: ctrl.map((p) => p.weighted_eff_ratio),
        line: { color: "#0072B2", width: 2, dash: "dash" },
        marker: { size: 7, color: "#0072B2" },
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Targeted 3-Hop Flow Ratio",
        x: tgt.map((p) => p.step_k),
        y: tgt.map((p) => p.three_hop_flow_ratio),
        line: { color: "#CC79A7", width: 2.5 },
        marker: { size: 7, color: "#CC79A7" },
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Matched-Ctrl 3-Hop Flow Ratio",
        x: ctrl.map((p) => p.step_k),
        y: ctrl.map((p) => p.three_hop_flow_ratio),
        line: { color: "#009E73", width: 2, dash: "dash" },
        marker: { size: 7, color: "#009E73" },
      },
    ];
  }, [neuroL0Summary]);

  const neuroL1DegradTraces = useMemo<PlotlyTrace[]>(() => {
    const condMap = neuroPilot?.condition_readout_means;
    if (!condMap) return [];
    const xLabels = NEURO_CONDITIONS_ORDER.map((c) => NEURO_COND_SHORT[c] ?? c);
    return [
      {
        type: "bar",
        name: "MN9_right (...660219265)",
        x: xLabels,
        y: NEURO_CONDITIONS_ORDER.map((c) => condMap[c]?.mn9_right_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: NEURO_CONDITIONS_ORDER.map((c) => condMap[c]?.mn9_right_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#D55E00" },
      },
      {
        type: "bar",
        name: "MN9_left (...645521262)",
        x: xLabels,
        y: NEURO_CONDITIONS_ORDER.map((c) => condMap[c]?.mn9_left_mean_hz ?? 0),
        error_y: {
          type: "data",
          array: NEURO_CONDITIONS_ORDER.map((c) => condMap[c]?.mn9_left_sd_hz ?? 0),
          visible: true,
        },
        marker: { color: "#0072B2" },
      },
    ];
  }, [neuroPilot]);

  const addL2PiTraces = useMemo<PlotlyTrace[]>(() => {
    if (!addL2Paradigm) return [];
    const phases = ["naive", "acquisition", "extinction", "reinstatement"];
    const phaseLabels = ["Naive (10s)", "Acquisition (145s)", "Extinction (235s)", "Reinstatement (310s)"];
    const armDefs: Array<{ id: string; color: string }> = [
      { id: "paired_conditioning", color: "#0072B2" },
      { id: "spontaneous_recovery_only", color: "#009E73" },
      { id: "yoked_unpaired", color: "#E69F00" },
      { id: "sham_no_stimulus", color: "#64748B" },
      { id: "dan_blocked", color: "#CC79A7" },
    ];
    return armDefs
      .filter((a) => Boolean(addL2Paradigm.arms[a.id]))
      .map((a) => ({
        type: "scatter" as const,
        mode: "lines+markers" as const,
        name: a.id,
        x: phaseLabels,
        y: phases.map((ph) => addL2Paradigm.arms[a.id]?.phase_snapshots?.[ph]?.pi_proxy ?? 0),
        line: { color: a.color, width: 2.5 },
        marker: { size: 8, color: a.color },
      }));
  }, [addL2Paradigm]);

  const addL2WeightTraces = useMemo<PlotlyTrace[]>(() => {
    const paired = addL2Paradigm?.arms?.paired_conditioning?.phase_snapshots;
    if (!paired) return [];
    const phases = ["naive", "acquisition", "extinction", "reinstatement"];
    const phaseLabels = ["Naive (10s)", "Acquisition (145s)", "Extinction (235s)", "Reinstatement (310s)"];
    return [
      {
        type: "scatter",
        mode: "lines+markers",
        name: "w_avoid (CS+)",
        x: phaseLabels,
        y: phases.map((ph) => paired[ph]?.w_avoid_cs_plus ?? 1.0),
        line: { color: "#D55E00", width: 2.5 },
        marker: { size: 8, color: "#D55E00" },
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "w_appr (CS+)",
        x: phaseLabels,
        y: phases.map((ph) => paired[ph]?.w_appr_cs_plus ?? 1.0),
        line: { color: "#0072B2", width: 2.5 },
        marker: { size: 8, color: "#0072B2" },
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "w_avoid (CS-)",
        x: phaseLabels,
        y: phases.map((ph) => paired[ph]?.w_avoid_cs_minus ?? 1.0),
        line: { color: "#009E73", width: 2, dash: "dash" },
        marker: { size: 7, color: "#009E73" },
      },
    ];
  }, [addL2Paradigm]);

  const addL1MbonTraces = useMemo<PlotlyTrace[]>(() => {
    const cohorts = addPilot?.cohort_stim_mean_hz;
    if (!cohorts) return [];
    const xLabels = ADDICTION_CONDITIONS_ORDER.map((c) => ADDICTION_COND_SHORT[c] ?? c);
    return [
      { key: "mbon02_avoid", label: "MBON02 (Avoid GLUT)", color: "#D55E00" },
      { key: "mbon14_appr", label: "MBON14 (Appr ACH)", color: "#0072B2" },
      { key: "mbon18_appr", label: "MBON18 (Appr ACH)", color: "#009E73" },
      { key: "mbon12_appr", label: "MBON12 (Appr ACH)", color: "#56B4E9" },
    ]
      .filter((item) => Boolean(cohorts[item.key]))
      .map((item) => ({
        type: "bar" as const,
        name: item.label,
        x: xLabels,
        y: ADDICTION_CONDITIONS_ORDER.map((c) => cohorts[item.key]?.[c] ?? 0),
        marker: { color: item.color },
      }));
  }, [addPilot]);

  const sleepPrcTraces = useMemo<PlotlyTrace[]>(() => {
    const curve = sleepL3Gate?.gates.light_pulse_prc.curve ?? [];
    if (curve.length === 0) return [];
    const shifts = curve.map((pt) => pt.phase_shift_h ?? 0);
    return [
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Phase Shift (h)",
        x: curve.map((pt) => `CT ${pt.ct_hours}`),
        y: shifts,
        line: { color: "#0072B2", width: 2.5 },
        marker: {
          size: 9,
          color: shifts.map((s) => (s > 0.15 ? "#009E73" : s < -0.15 ? "#D55E00" : "#64748B")),
        },
      },
    ];
  }, [sleepL3Gate]);

  const sleepShiftTraces = useMemo<PlotlyTrace[]>(() => {
    if (!sleepShift) return [];
    const arms = Object.values(sleepShift.arms);
    if (arms.length === 0) return [];
    return [
      {
        type: "bar",
        name: t("sleepColMaxErr"),
        x: arms.map((a) => a.arm_id),
        y: arms.map((a) => a.max_abs_phase_error_h),
        marker: {
          color: arms.map((a) => (a.days_to_reentrain === null ? "#D55E00" : "#0072B2")),
        },
      },
    ];
  }, [sleepShift, t]);

  const sleepPilotTutubTraces = useMemo<PlotlyTrace[]>(() => {
    const cohorts = sleepPilot?.cohort_stim_mean_hz;
    if (!cohorts || !cohorts.tutub_b_interneuron) return [];
    return [
      {
        type: "bar",
        name: "TuTuB_b (2 GLUT)",
        x: SLEEP_CONDITIONS_ORDER.map((c) => SLEEP_COND_SHORT[c] ?? c),
        y: SLEEP_CONDITIONS_ORDER.map((c) => cohorts.tutub_b_interneuron?.[c] ?? 0),
        marker: { color: "#E69F00" },
      },
    ];
  }, [sleepPilot]);

  const sleepPilotEbTraces = useMemo<PlotlyTrace[]>(() => {
    const cohorts = sleepPilot?.cohort_stim_mean_hz;
    if (!cohorts) return [];
    const xLabels = SLEEP_CONDITIONS_ORDER.map((c) => SLEEP_COND_SHORT[c] ?? c);
    return [
      { key: "tubu01_relay", label: "TuBu01 (10 ACH)", color: "#0072B2" },
      { key: "tubu06_relay", label: "TuBu06 (10 ACH)", color: "#56B4E9" },
      { key: "exr1_helicon", label: "ExR1 (4 ACH)", color: "#009E73" },
      { key: "er5_sleep_homeostat", label: "ER5 (21 GABA)", color: "#D55E00" },
    ]
      .filter((item) => Boolean(cohorts[item.key]))
      .map((item) => ({
        type: "bar" as const,
        name: item.label,
        x: xLabels,
        y: SLEEP_CONDITIONS_ORDER.map((c) => cohorts[item.key]?.[c] ?? 0),
        marker: { color: item.color },
      }));
  }, [sleepPilot]);

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
          aria-pressed={activeSubTab === "stress"}
          onClick={() => onSelectSubTab("stress")}
        >
          <span>{t("tabStress")}</span>
          <StatusBadge
            label={stressL3Gate || stressPilot ? t("stateExperimental") : t("statePlanned")}
            tone={stressL3Gate || stressPilot ? "info" : "neutral"}
          />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "pharma"}
          onClick={() => onSelectSubTab("pharma")}
        >
          <span>{t("tabPharma")}</span>
          <StatusBadge
            label={pharmaL2Gate || pharmaPilot ? t("stateExperimental") : t("statePlanned")}
            tone={pharmaL2Gate || pharmaPilot ? "info" : "neutral"}
          />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "neuro"}
          onClick={() => onSelectSubTab("neuro")}
        >
          <span>{t("tabNeuro")}</span>
          <StatusBadge
            label={neuroL0Gate || neuroPilot ? t("stateExperimental") : t("statePlanned")}
            tone={neuroL0Gate || neuroPilot ? "info" : "neutral"}
          />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "addiction"}
          onClick={() => onSelectSubTab("addiction")}
        >
          <span>{t("tabAddiction")}</span>
          <StatusBadge
            label={addL2Gate || addPilot ? t("stateExperimental") : t("statePlanned")}
            tone={addL2Gate || addPilot ? "info" : "neutral"}
          />
        </button>
        <button
          type="button"
          className="pill-btn"
          aria-pressed={activeSubTab === "sleep"}
          onClick={() => onSelectSubTab("sleep")}
        >
          <span>{t("tabSleep")}</span>
          <StatusBadge
            label={sleepL3Gate || sleepPilot ? t("stateExperimental") : t("statePlanned")}
            tone={sleepL3Gate || sleepPilot ? "info" : "neutral"}
          />
        </button>
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

      {activeSubTab === "stress" && (
        <>
          {!stressL3Gate && !stressPilot ? (
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
                    <h2>{t("stressBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      stress_allostatic_reactive_scope_v1 (L3) + malecns_v1_0 · synapse_lif_v1 (L1){" "}
                      {stressPilot?.git_commits?.[0] ? `· git ${stressPilot.git_commits[0].slice(0, 8)}` : ""}
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
                          seedIds: "10001, 10010, 11177, 10783, 13109, 11832",
                          hops: 1,
                          direction: "both",
                          minSynapses: 15,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>

                {stressL3Gate && (
                  <div className="kpi-grid">
                    <div className="kpi-card">
                      <div className="kpi-label">{t("stressGateRk45")}</div>
                      <div className="kpi-value">
                        {stressL3Gate.gates.rk45_convergence_and_bounds.max_abs_diff.toExponential(2)}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            stressL3Gate.gates.rk45_convergence_and_bounds.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            stressL3Gate.gates.rk45_convergence_and_bounds.passed ? "ok" : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("stressGateSham")}</div>
                      <div className="kpi-value">
                        {stressL3Gate.gates.sham_baseline_invariance.sham_max_a.toFixed(1)} /{" "}
                        {stressL3Gate.gates.sham_baseline_invariance.sham_max_l.toFixed(1)}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            stressL3Gate.gates.sham_baseline_invariance.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={stressL3Gate.gates.sham_baseline_invariance.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("stressGateAcute")}</div>
                      <div className="kpi-value">
                        C={stressL3Gate.gates.acute_stress_habituation_and_recovery.acute_c_min.toFixed(3)}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            stressL3Gate.gates.acute_stress_habituation_and_recovery.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            stressL3Gate.gates.acute_stress_habituation_and_recovery.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("stressGateChronic")}</div>
                      <div className="kpi-value">
                        {stressL3Gate.gates.chronic_allostatic_overload_separation.chronic_vs_acute_load_ratio.toFixed(
                          2,
                        )}
                        x
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            stressL3Gate.gates.chronic_allostatic_overload_separation.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            stressL3Gate.gates.chronic_allostatic_overload_separation.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("stressGateWashout")}</div>
                      <div className="kpi-value">
                        C={stressL3Gate.gates.post_chronic_washout_and_ruo_guard.washout_c_end.toFixed(3)}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            stressL3Gate.gates.post_chronic_washout_and_ruo_guard.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            stressL3Gate.gates.post_chronic_washout_and_ruo_guard.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simpleStressTitle")}: </strong>
                  {t("simpleStressSummary")}
                </div>
              )}

              <div className="grid-2">
                {stressL3Panel && (
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("stressChartL3Title")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("stressChartL3Title")}
                      traces={stressL3TrajTraces}
                      layout={{
                        height: 320,
                        xaxis: { title: "Time (h)" },
                        yaxis: { title: "Normalized State (C / L)", rangemode: "tozero" },
                        margin: { l: 55, r: 20, t: 25, b: 55 },
                      }}
                    />
                  </div>
                )}

                {stressPilot && (
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("stressChartL1Title")}</h3>
                      <span className="mono" style={{ fontSize: "0.78rem" }}>
                        {stressPilot.succeeded_run_count}/{stressPilot.total_runs} succeeded · sham=
                        {stressPilot.sham_max_spikes}
                      </span>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("stressChartL1Title")}
                      traces={stressL1ReadoutTraces}
                      layout={{
                        barmode: "group",
                        height: 320,
                        yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                        xaxis: { tickangle: -18 },
                        margin: { l: 55, r: 20, t: 25, b: 85 },
                      }}
                    />
                  </div>
                )}
              </div>

              {uiMode === "expert" ? (
                <>
                  {stressL3Panel && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("stressSnapshotTableTitle")}</h3>
                      </div>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>{t("colContrast")}</th>
                              <th>L3 Source</th>
                              <th>Drive (Hz)</th>
                              <th>Inh Reserve Scale</th>
                              <th>DNp01 (Hz)</th>
                              <th>DNp09 (Hz)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {stressL3Panel.l3_to_l1_coupling_snapshots.map((snap) => {
                              const ro = stressPilot?.condition_readout_means?.[snap.condition_id];
                              return (
                                <tr key={snap.condition_id}>
                                  <td className="mono">{snap.condition_id}</td>
                                  <td>{snap.l3_state_source}</td>
                                  <td className="mono">{snap.threat_drive_hz.toFixed(0)}</td>
                                  <td className="mono">{snap.inhibitory_reserve_scale.toFixed(2)}x</td>
                                  <td className="mono">
                                    {ro ? ro.dnp01_escape_mean_hz.toFixed(3) : t("noneDash")}
                                  </td>
                                  <td className="mono">
                                    {ro ? ro.dnp09_freeze_mean_hz.toFixed(3) : t("noneDash")}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {stressPilot && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("stressContrastsTitle")}</h3>
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
                            </tr>
                          </thead>
                          <tbody>
                            {stressPilot.contrasts.map((row) => (
                              <tr key={row.contrast_name}>
                                <td className="mono">{row.contrast_name}</td>
                                <td className="mono">{row.neuron_id}</td>
                                <td>
                                  {row.baseline_mean_hz.toFixed(3)} ± {row.baseline_sd_hz.toFixed(3)}
                                </td>
                                <td>
                                  {row.treatment_mean_hz.toFixed(3)} ± {row.treatment_sd_hz.toFixed(3)}
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
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="alert" role="note">
                    <div>
                      <strong>{t("stressLimitsTitle")}: </strong>
                      <span>{t("stressLimitsBody")}</span>
                    </div>
                  </div>
                </>
              ) : (
                stressPilot && (
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
                          {stressPilot.contrasts.map((row) => (
                            <tr key={row.contrast_name}>
                              <td className="mono">{row.contrast_name}</td>
                              <td className="mono">{row.neuron_id}</td>
                              <td>
                                <strong>
                                  {row.mean_difference_hz >= 0 ? "+" : ""}
                                  {row.mean_difference_hz.toFixed(3)} Hz
                                </strong>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )
              )}
            </>
          )}
        </>
      )}

      {activeSubTab === "pharma" && (
        <>
          {!pharmaL2Gate && !pharmaPilot ? (
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
                    <h2>{t("pharmaBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      receptor_conductance_modulation_v1 (L2) + malecns_v1_0 · synapse_lif_v1 (L1){" "}
                      {pharmaPilot?.git_commits?.[0] ? `· git ${pharmaPilot.git_commits[0].slice(0, 8)}` : ""}
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
                          seedIds: "523539, 558778, 10592, 902566, 811380",
                          hops: 1,
                          direction: "both",
                          minSynapses: 15,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>

                {pharmaL2Gate && (
                  <div className="kpi-grid">
                    <div className="kpi-card">
                      <div className="kpi-label">{t("pharmaGateHill")}</div>
                      <div className="kpi-value">0 / 0.5 / 1.0</div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            pharmaL2Gate.gates.hill_boundary_and_half_max.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={pharmaL2Gate.gates.hill_boundary_and_half_max.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("pharmaGateSchild")}</div>
                      <div className="kpi-value">
                        {pharmaL2Gate.gates.schild_linearity_and_slope.schild_slope.toFixed(6)}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            pharmaL2Gate.gates.schild_linearity_and_slope.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            pharmaL2Gate.gates.schild_linearity_and_slope.passed ? "ok" : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("pharmaGateBidir")}</div>
                      <div className="kpi-value">
                        {pharmaL2Gate.gates.noncompetitive_vs_pam_directionality.antag_scale_at_ic50.toFixed(
                          1,
                        )}{" "}
                        vs{" "}
                        {pharmaL2Gate.gates.noncompetitive_vs_pam_directionality.pam_scale_at_km.toFixed(
                          1,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            pharmaL2Gate.gates.noncompetitive_vs_pam_directionality.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            pharmaL2Gate.gates.noncompetitive_vs_pam_directionality.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("pharmaGateBliss")}</div>
                      <div className="kpi-value">
                        {pharmaL2Gate.gates.bliss_independence_identity.bliss_0_5_plus_0_5.toFixed(
                          2,
                        )}{" "}
                        /{" "}
                        {pharmaL2Gate.gates.bliss_independence_identity.bliss_0_3_plus_0_4.toFixed(
                          2,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            pharmaL2Gate.gates.bliss_independence_identity.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            pharmaL2Gate.gates.bliss_independence_identity.passed ? "ok" : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("pharmaGateRuo")}</div>
                      <div className="kpi-value">
                        named={String(pharmaL2Gate.gates.ruo_dose_independent_guard.named_compound_gate_enabled)}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            pharmaL2Gate.gates.ruo_dose_independent_guard.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={pharmaL2Gate.gates.ruo_dose_independent_guard.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simplePharmaTitle")}: </strong>
                  {t("simplePharmaSummary")}
                </div>
              )}

              <div className="grid-2">
                {pharmaL2Panel && (
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("pharmaChartL2Title")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("pharmaChartL2Title")}
                      traces={pharmaL2CurveTraces}
                      layout={{
                        height: 320,
                        xaxis: { title: "log10([Ligand] / Reference Affinity)" },
                        yaxis: { title: "Conductance Scale Factor", range: [0, 2.1] },
                        margin: { l: 55, r: 20, t: 25, b: 55 },
                      }}
                    />
                  </div>
                )}

                {pharmaPilot && (
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("pharmaChartL1Title")}</h3>
                      <span className="mono" style={{ fontSize: "0.78rem" }}>
                        {pharmaPilot.succeeded_run_count}/{pharmaPilot.total_runs} succeeded · sham=
                        {pharmaPilot.sham_max_spikes}
                      </span>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("pharmaChartL1Title")}
                      traces={pharmaL1ReadoutTraces}
                      layout={{
                        barmode: "group",
                        height: 320,
                        yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                        xaxis: { tickangle: -18 },
                        margin: { l: 55, r: 20, t: 25, b: 85 },
                      }}
                    />
                  </div>
                )}
              </div>

              {uiMode === "expert" ? (
                <>
                  {pharmaL2Panel && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("pharmaSnapshotTableTitle")}</h3>
                      </div>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>{t("colContrast")}</th>
                              <th>Target</th>
                              <th>Ratio / Label</th>
                              <th>Rdl Scale</th>
                              <th>nAChR Scale</th>
                              <th>523539 (Hz)</th>
                              <th>558778 (Hz)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pharmaL2Panel.l1_coupling_snapshots.map((snap) => {
                              const ro = pharmaPilot?.condition_readout_means?.[snap.condition_id];
                              return (
                                <tr key={snap.condition_id}>
                                  <td className="mono">{snap.condition_id}</td>
                                  <td>{snap.receptor_target}</td>
                                  <td className="mono">{snap.normalized_ratio_label}</td>
                                  <td className="mono">{snap.rdl_gaba_scale.toFixed(2)}x</td>
                                  <td className="mono">{snap.nachr_ach_scale.toFixed(2)}x</td>
                                  <td className="mono">
                                    {ro ? ro.anxxx027_l_523539_mean_hz.toFixed(3) : t("noneDash")}
                                  </td>
                                  <td className="mono">
                                    {ro ? ro.an08b012_r_558778_mean_hz.toFixed(3) : t("noneDash")}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      {pharmaPilot?.bliss_evaluation && (
                        <div className="meta-strip" style={{ marginTop: 10 }}>
                          <span className="mono">
                            523539 Bliss null={pharmaPilot.bliss_evaluation.expected_bliss_suppression_523539.toFixed(4)}{" "}
                            vs observed={pharmaPilot.bliss_evaluation.observed_combined_suppression_523539.toFixed(4)}{" "}
                            (excess={pharmaPilot.bliss_evaluation.bliss_excess_vs_null_523539 >= 0 ? "+" : ""}
                            {pharmaPilot.bliss_evaluation.bliss_excess_vs_null_523539.toFixed(4)})
                          </span>
                          <span className="mono">
                            558778 Bliss null={pharmaPilot.bliss_evaluation.expected_bliss_suppression_558778.toFixed(4)}{" "}
                            vs observed={pharmaPilot.bliss_evaluation.observed_combined_suppression_558778.toFixed(4)}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {pharmaPilot && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("pharmaContrastsTitle")}</h3>
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
                            </tr>
                          </thead>
                          <tbody>
                            {pharmaPilot.contrasts.map((row) => (
                              <tr key={row.contrast_name}>
                                <td className="mono">{row.contrast_name}</td>
                                <td className="mono">{row.neuron_id}</td>
                                <td>
                                  {row.baseline_mean_hz.toFixed(3)} ± {row.baseline_sd_hz.toFixed(3)}
                                </td>
                                <td>
                                  {row.treatment_mean_hz.toFixed(3)} ± {row.treatment_sd_hz.toFixed(3)}
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
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="alert" role="note">
                    <div>
                      <strong>{t("pharmaLimitsTitle")}: </strong>
                      <span>{t("pharmaLimitsBody")}</span>
                    </div>
                  </div>
                </>
              ) : (
                pharmaPilot && (
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
                          {pharmaPilot.contrasts.map((row) => (
                            <tr key={row.contrast_name}>
                              <td className="mono">{row.contrast_name}</td>
                              <td className="mono">{row.neuron_id}</td>
                              <td>
                                <strong>
                                  {row.mean_difference_hz >= 0 ? "+" : ""}
                                  {row.mean_difference_hz.toFixed(3)} Hz
                                </strong>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )
              )}
            </>
          )}
        </>
      )}

      {activeSubTab === "neuro" && (
        <>
          {!neuroL0Gate && !neuroPilot ? (
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
                    <h2>{t("neuroBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      neuro_topology_ablation_v1 (L0) + flywire_fafb_v630 · shiu2024_lif (L1){" "}
                      {neuroPilot?.git_commits?.[0] ? `· git ${neuroPilot.git_commits[0].slice(0, 8)}` : ""}
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
                          seedIds:
                            "720575940660219265, 720575940645521262, 720575940623211725, 720575940619853515, 720575940607272649, 720575940626038714",
                          hops: 1,
                          direction: "both",
                          minSynapses: 15,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>

                {neuroL0Gate && (
                  <div className="kpi-grid">
                    <div className="kpi-card">
                      <div className="kpi-label">{t("neuroGateChain")}</div>
                      <div className="kpi-value">
                        {neuroL0Gate.gates.chain_cut_disconnects.cut_largest_wcc_fraction.toFixed(
                          2,
                        )}{" "}
                        WCC
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            neuroL0Gate.gates.chain_cut_disconnects.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={neuroL0Gate.gates.chain_cut_disconnects.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("neuroGateBridge")}</div>
                      <div className="kpi-value">
                        {neuroL0Gate.gates.parallel_bridge_node_vs_edge_dissociation.edge_cut_3hop_flow.toFixed(
                          0,
                        )}{" "}
                        vs 0
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            neuroL0Gate.gates.parallel_bridge_node_vs_edge_dissociation.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            neuroL0Gate.gates.parallel_bridge_node_vs_edge_dissociation.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("neuroGateParity")}</div>
                      <div className="kpi-value">
                        {neuroL0Gate.gates.asymmetric_orientation_and_reverse_dijkstra_parity.reverse_dijkstra_weighted_eff.toFixed(
                          2,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            neuroL0Gate.gates.asymmetric_orientation_and_reverse_dijkstra_parity
                              .passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            neuroL0Gate.gates.asymmetric_orientation_and_reverse_dijkstra_parity
                              .passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("neuroGateFrac")}</div>
                      <div className="kpi-value">
                        {neuroL0Gate.gates.fractional_synapse_scaling_monotonicity.flow_half.toFixed(
                          0,
                        )}{" "}
                        / 200
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            neuroL0Gate.gates.fractional_synapse_scaling_monotonicity.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            neuroL0Gate.gates.fractional_synapse_scaling_monotonicity.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("neuroGateCtrl")}</div>
                      <div className="kpi-value">
                        {String(
                          neuroL0Gate.gates.isolated_control_invariance_and_immutability
                            .graph_sha_unchanged,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            neuroL0Gate.gates.isolated_control_invariance_and_immutability.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            neuroL0Gate.gates.isolated_control_invariance_and_immutability.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simpleNeuroTitle")}: </strong>
                  {t("simpleNeuroSummary")}
                </div>
              )}

              <div className="grid-2">
                {neuroL0Summary && (
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("neuroChartL0CurveTitle")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("neuroChartL0CurveTitle")}
                      traces={neuroL0CurveTraces}
                      layout={{
                        height: 320,
                        xaxis: { title: "Ablated Hubs / Controls (k)" },
                        yaxis: { title: "Ratio vs Intact", range: [0, 1.08] },
                        margin: { l: 55, r: 20, t: 25, b: 55 },
                      }}
                    />
                  </div>
                )}

                {neuroPilot && (
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("neuroChartL1DegradTitle")}</h3>
                      <span className="mono" style={{ fontSize: "0.78rem" }}>
                        {neuroPilot.succeeded_run_count}/{neuroPilot.total_runs} succeeded · sham=
                        {neuroPilot.sham_max_spikes}
                      </span>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("neuroChartL1DegradTitle")}
                      traces={neuroL1DegradTraces}
                      layout={{
                        barmode: "group",
                        height: 320,
                        yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                        xaxis: { tickangle: -18 },
                        margin: { l: 55, r: 20, t: 25, b: 85 },
                      }}
                    />
                  </div>
                )}
              </div>

              {uiMode === "expert" ? (
                <>
                  {neuroPilot && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("neuroAuditTableTitle")}</h3>
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
                            </tr>
                          </thead>
                          <tbody>
                            {neuroPilot.contrasts.map((row) => (
                              <tr key={row.contrast_name}>
                                <td className="mono">{row.contrast_name}</td>
                                <td className="mono">{row.neuron_id}</td>
                                <td>
                                  {row.baseline_mean_hz.toFixed(3)} ±{" "}
                                  {row.baseline_sd_hz.toFixed(3)}
                                </td>
                                <td>
                                  {row.treatment_mean_hz.toFixed(3)} ±{" "}
                                  {row.treatment_sd_hz.toFixed(3)}
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
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {neuroMalecns && (
                    <div className="card">
                      <div className="card-header">
                        <div>
                          <h3>{t("neuroMalecnsTitle")}</h3>
                          <p className="card-subtitle mono">
                            {neuroMalecns.dataset_id} ({neuroMalecns.specimen_id}) · max|SMD|=
                            {neuroMalecns.matched_control_max_abs_smd.toFixed(4)}
                          </p>
                        </div>
                        <StatusBadge label={t("bioRuoBadge")} tone="info" />
                      </div>
                      <p style={{ fontSize: "0.84rem", color: "var(--text-secondary)", marginTop: 0 }}>
                        {neuroMalecns.specimen_isolation_note}
                      </p>
                      <div className="meta-strip">
                        {neuroMalecns.curve_points
                          .filter((p) => p.step_k === 12)
                          .map((p) => (
                            <span key={p.ablation_id} className="mono">
                              {p.arm_type} (k=12): eff={p.weighted_eff_ratio.toFixed(4)} · 3hop=
                              {p.three_hop_flow_ratio.toFixed(4)}
                            </span>
                          ))}
                      </div>
                    </div>
                  )}

                  <div className="alert" role="note">
                    <div>
                      <strong>{t("neuroLimitsTitle")}: </strong>
                      <span>{t("neuroLimitsBody")}</span>
                    </div>
                  </div>
                </>
              ) : (
                neuroPilot && (
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
                          {neuroPilot.contrasts.map((row) => (
                            <tr key={row.contrast_name}>
                              <td className="mono">{row.contrast_name}</td>
                              <td className="mono">{row.neuron_id}</td>
                              <td>
                                <strong>
                                  {row.mean_difference_hz >= 0 ? "+" : ""}
                                  {row.mean_difference_hz.toFixed(3)} Hz
                                </strong>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )
              )}
            </>
          )}
        </>
      )}

      {activeSubTab === "addiction" && (
        <>
          {!addL2Gate && !addPilot ? (
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
                    <h2>{t("addictionBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      mb_dopamine_plasticity_v1 (L2) + malecns_v1_0 · synapse_lif_v1 (L1){" "}
                      {addPilot?.git_commits?.[0] ? `· git ${addPilot.git_commits[0].slice(0, 8)}` : ""}
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
                          seedIds: "522749, 522444, 13728, 10267, 512788, 10977",
                          hops: 1,
                          direction: "both",
                          minSynapses: 30,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>

                {addL2Gate && (
                  <div className="kpi-grid">
                    <div className="kpi-card">
                      <div className="kpi-label">{t("addGateConv")}</div>
                      <div className="kpi-value">
                        {addL2Gate.gates.numerical_convergence_and_bounds.max_abs_weight_diff.toExponential(
                          2,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            addL2Gate.gates.numerical_convergence_and_bounds.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            addL2Gate.gates.numerical_convergence_and_bounds.passed ? "ok" : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("addGateAcq")}</div>
                      <div className="kpi-value">
                        +{addL2Gate.gates.acquisition_specificity.pi_acq.toFixed(3)} PI
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            addL2Gate.gates.acquisition_specificity.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={addL2Gate.gates.acquisition_specificity.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("addGateExt")}</div>
                      <div className="kpi-value">
                        {addL2Gate.gates.parallel_memory_extinction.pi_ext.toFixed(3)} PI
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            addL2Gate.gates.parallel_memory_extinction.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            addL2Gate.gates.parallel_memory_extinction.passed ? "ok" : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("addGateReinst")}</div>
                      <div className="kpi-value">
                        +{addL2Gate.gates.reinstatement_recovery.pi_reinst.toFixed(3)} PI
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            addL2Gate.gates.reinstatement_recovery.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={addL2Gate.gates.reinstatement_recovery.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("addGateCtrl")}</div>
                      <div className="kpi-value">
                        {addL2Gate.gates.negative_controls_null.yoked_unpaired_acq_pi.toExponential(
                          1,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            addL2Gate.gates.negative_controls_null.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={addL2Gate.gates.negative_controls_null.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simpleAddictionTitle")}: </strong>
                  {t("simpleAddictionSummary")}
                </div>
              )}

              {addL2Paradigm && (
                <div className="grid-2">
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("addChartL2PiTitle")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("addChartL2PiTitle")}
                      traces={addL2PiTraces}
                      layout={{
                        height: 320,
                        yaxis: { title: "Preference Index (PI)" },
                        margin: { l: 55, r: 20, t: 25, b: 60 },
                      }}
                    />
                  </div>
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("addChartL2WeightsTitle")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("addChartL2WeightsTitle")}
                      traces={addL2WeightTraces}
                      layout={{
                        height: 320,
                        yaxis: { title: "Normalized Weight", range: [0.1, 1.05] },
                        margin: { l: 55, r: 20, t: 25, b: 60 },
                      }}
                    />
                  </div>
                </div>
              )}

              {uiMode === "expert" ? (
                <>
                  {addPilot && (
                    <>
                      <div className="card">
                        <div className="card-header">
                          <h3>{t("addChartL1MbonTitle")}</h3>
                          <span className="mono" style={{ fontSize: "0.78rem" }}>
                            {addPilot.succeeded_run_count}/{addPilot.total_runs} succeeded · sham=
                            {addPilot.sham_max_spikes}
                          </span>
                        </div>
                        <PlotlyChart
                          theme={theme}
                          ariaLabel={t("addChartL1MbonTitle")}
                          traces={addL1MbonTraces}
                          layout={{
                            barmode: "group",
                            height: 340,
                            yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                            xaxis: { tickangle: -18 },
                            margin: { l: 55, r: 20, t: 25, b: 85 },
                          }}
                        />
                      </div>

                      <div className="card">
                        <div className="card-header">
                          <h3>{t("addL1ContrastsTitle")}</h3>
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
                              </tr>
                            </thead>
                            <tbody>
                              {addPilot.contrasts.map((row) => (
                                <tr key={row.contrast_name}>
                                  <td className="mono">{row.contrast_name}</td>
                                  <td className="mono">{row.neuron_id}</td>
                                  <td>
                                    {row.baseline_mean_hz.toFixed(3)} ±{" "}
                                    {row.baseline_sd_hz.toFixed(3)}
                                  </td>
                                  <td>
                                    {row.treatment_mean_hz.toFixed(3)} ±{" "}
                                    {row.treatment_sd_hz.toFixed(3)}
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
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  )}

                  <div className="alert" role="note">
                    <div>
                      <strong>{t("addLimitsTitle")}: </strong>
                      <span>{t("addLimitsBody")}</span>
                    </div>
                  </div>
                </>
              ) : (
                addPilot && (
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
                          {addPilot.contrasts.map((row) => (
                            <tr key={row.contrast_name}>
                              <td className="mono">{row.contrast_name}</td>
                              <td className="mono">{row.neuron_id}</td>
                              <td>
                                <strong>
                                  {row.mean_difference_hz >= 0 ? "+" : ""}
                                  {row.mean_difference_hz.toFixed(3)} Hz
                                </strong>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )
              )}
            </>
          )}
        </>
      )}

      {activeSubTab === "sleep" && (
        <>
          {!sleepL3Gate && !sleepPilot ? (
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
                    <h2>{t("sleepBannerTitle")}</h2>
                    <p className="card-subtitle mono">
                      leloup_goldbeter_1998_two_process_v1 (L3) + malecns_v1_0 · synapse_lif_v1 (L1){" "}
                      {sleepPilot?.git_commits?.[0]
                        ? `· git ${sleepPilot.git_commits[0].slice(0, 8)}`
                        : ""}
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
                          seedIds: "10324, 15016, 114115, 112789, 10043",
                          hops: 1,
                          direction: "both",
                          minSynapses: 25,
                          maxNodes: 75,
                        })
                      }
                    >
                      {t("exploreIn3d")}
                    </button>
                  </div>
                </div>

                {sleepL3Gate && (
                  <div className="kpi-grid">
                    <div className="kpi-card">
                      <div className="kpi-label">{t("sleepGateDd")}</div>
                      <div className="kpi-value">
                        {sleepL3Gate.gates.dd_free_running_and_convergence.tau_dd_coarse_h?.toFixed(
                          2,
                        ) ?? t("noneDash")}{" "}
                        h
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            sleepL3Gate.gates.dd_free_running_and_convergence.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            sleepL3Gate.gates.dd_free_running_and_convergence.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("sleepGateLd")}</div>
                      <div className="kpi-value">
                        {sleepL3Gate.gates.ld12_12_entrainment.tau_ld_h?.toFixed(2) ??
                          t("noneDash")}{" "}
                        h
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            sleepL3Gate.gates.ld12_12_entrainment.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={sleepL3Gate.gates.ld12_12_entrainment.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("sleepGatePrc")}</div>
                      <div className="kpi-value">
                        {sleepL3Gate.gates.light_pulse_prc.max_early_night_delay_h?.toFixed(2) ??
                          t("noneDash")}{" "}
                        / +
                        {sleepL3Gate.gates.light_pulse_prc.late_night_ct21_advance_h?.toFixed(2) ??
                          t("noneDash")}{" "}
                        h
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            sleepL3Gate.gates.light_pulse_prc.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={sleepL3Gate.gates.light_pulse_prc.passed ? "ok" : "warn"}
                        />
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-label">{t("sleepGateRebound")}</div>
                      <div className="kpi-value">
                        +
                        {sleepL3Gate.gates.homeostatic_deprivation_rebound.recovery_rest_fraction_delta.toFixed(
                          3,
                        )}
                      </div>
                      <div className="kpi-sub">
                        <StatusBadge
                          label={
                            sleepL3Gate.gates.homeostatic_deprivation_rebound.passed
                              ? t("statusPass")
                              : t("statusFail")
                          }
                          tone={
                            sleepL3Gate.gates.homeostatic_deprivation_rebound.passed
                              ? "ok"
                              : "warn"
                          }
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {uiMode === "simple" && (
                <div className="notice-box" style={{ marginBottom: 12 }}>
                  <strong>{t("simpleSleepTitle")}: </strong>
                  {t("simpleSleepSummary")}
                </div>
              )}

              {sleepL3Gate && (
                <div className="grid-2">
                  <div className="card">
                    <div className="card-header">
                      <h3>{t("sleepChartPrcTitle")}</h3>
                    </div>
                    <PlotlyChart
                      theme={theme}
                      ariaLabel={t("sleepChartPrcTitle")}
                      traces={sleepPrcTraces}
                      layout={{
                        height: 320,
                        yaxis: { title: "Phase Shift (h)" },
                        margin: { l: 55, r: 20, t: 25, b: 50 },
                      }}
                    />
                  </div>
                  {sleepShift && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("sleepChartShiftTitle")}</h3>
                      </div>
                      <PlotlyChart
                        theme={theme}
                        ariaLabel={t("sleepChartShiftTitle")}
                        traces={sleepShiftTraces}
                        layout={{
                          height: 320,
                          yaxis: { title: t("sleepColMaxErr"), rangemode: "tozero" },
                          xaxis: { tickangle: -18 },
                          margin: { l: 55, r: 20, t: 25, b: 85 },
                        }}
                      />
                    </div>
                  )}
                </div>
              )}

              {uiMode === "expert" ? (
                <>
                  {sleepShift && (
                    <div className="card">
                      <div className="card-header">
                        <h3>{t("sleepChartShiftTitle")}</h3>
                      </div>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>{t("sleepColArm")}</th>
                              <th>{t("sleepColMaxErr")}</th>
                              <th>{t("sleepColReentrain")}</th>
                              <th>{t("sleepColSPeak")}</th>
                              <th>{t("sleepColRestFrac")}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.values(sleepShift.arms).map((arm) => (
                              <tr key={arm.arm_id}>
                                <td className="mono">{arm.arm_id}</td>
                                <td className="mono">{arm.max_abs_phase_error_h.toFixed(3)}</td>
                                <td className="mono">
                                  {arm.days_to_reentrain !== null
                                    ? arm.days_to_reentrain.toFixed(3)
                                    : t("sleepNeverReentrained")}
                                </td>
                                <td className="mono">{arm.s_peak_overall.toFixed(4)}</td>
                                <td className="mono">
                                  {arm.modeled_rest_fraction_post_onset.toFixed(4)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {sleepPilot && (
                    <>
                      <div className="grid-2">
                        <div className="card">
                          <div className="card-header">
                            <h3>{t("sleepChartPilotTutubTitle")}</h3>
                          </div>
                          <PlotlyChart
                            theme={theme}
                            ariaLabel={t("sleepChartPilotTutubTitle")}
                            traces={sleepPilotTutubTraces}
                            layout={{
                              height: 330,
                              yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                              xaxis: { tickangle: -20 },
                              margin: { l: 55, r: 20, t: 25, b: 85 },
                            }}
                          />
                        </div>
                        <div className="card">
                          <div className="card-header">
                            <h3>{t("sleepChartPilotEbTitle")}</h3>
                          </div>
                          <PlotlyChart
                            theme={theme}
                            ariaLabel={t("sleepChartPilotEbTitle")}
                            traces={sleepPilotEbTraces}
                            layout={{
                              barmode: "group",
                              height: 330,
                              yaxis: { title: t("chartYAxisHz"), rangemode: "tozero" },
                              xaxis: { tickangle: -20 },
                              margin: { l: 55, r: 20, t: 25, b: 85 },
                            }}
                          />
                        </div>
                      </div>

                      <div className="card">
                        <div className="card-header">
                          <h3>{t("sleepL1ContrastsTitle")}</h3>
                          <span className="mono" style={{ fontSize: "0.78rem" }}>
                            {sleepPilot.succeeded_run_count}/{sleepPilot.total_runs} succeeded · sham=
                            {sleepPilot.sham_max_spikes}
                          </span>
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
                              </tr>
                            </thead>
                            <tbody>
                              {sleepPilot.contrasts.map((row) => (
                                <tr key={row.contrast_name}>
                                  <td className="mono">{row.contrast_name}</td>
                                  <td className="mono">{row.neuron_id}</td>
                                  <td>
                                    {row.baseline_mean_hz.toFixed(3)} ±{" "}
                                    {row.baseline_sd_hz.toFixed(3)}
                                  </td>
                                  <td>
                                    {row.treatment_mean_hz.toFixed(3)} ±{" "}
                                    {row.treatment_sd_hz.toFixed(3)}
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
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  )}

                  <div className="alert" role="note">
                    <div>
                      <strong>{t("sleepLimitsTitle")}: </strong>
                      <span>{t("sleepLimitsBody")}</span>
                    </div>
                  </div>
                </>
              ) : (
                sleepPilot && (
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
                          {sleepPilot.contrasts.map((row) => (
                            <tr key={row.contrast_name}>
                              <td className="mono">{row.contrast_name}</td>
                              <td className="mono">{row.neuron_id}</td>
                              <td>
                                <strong>
                                  {row.mean_difference_hz >= 0 ? "+" : ""}
                                  {row.mean_difference_hz.toFixed(3)} Hz
                                </strong>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )
              )}
            </>
          )}
        </>
      )}

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

      {activeSubTab === "planned" &&
        (plannedModules.length === 0 ? (
          <div className="card">
            <div className="card-header">
              <div>
                <h3>{t("plannedAllActiveTitle")}</h3>
                <p className="card-subtitle">{t("plannedAllActiveBody")}</p>
              </div>
              <StatusBadge label={t("stateExperimental")} tone="ok" />
            </div>
          </div>
        ) : (
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
        ))}
    </section>
  );
};
