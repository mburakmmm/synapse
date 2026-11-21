import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { SubgraphResponse } from "../api";
import { useI18n } from "../i18n/LanguageContext";
import { StatusBadge } from "./StatusBadge";

const NT_HEX: Record<string, number> = {
  ACH: 0x38bdf8,
  GABA: 0xf43f5e,
  GLUT: 0xf59e0b,
  DA: 0xa78bfa,
  SER: 0x10b981,
  OCT: 0x2dd4bf,
  UNKNOWN: 0x94a3b8,
};

const NT_CSS: Record<string, string> = {
  ACH: "#38bdf8",
  GABA: "#f43f5e",
  GLUT: "#f59e0b",
  DA: "#a78bfa",
  SER: "#10b981",
  OCT: "#2dd4bf",
  UNKNOWN: "#94a3b8",
};

function ntHex(nt: string | null | undefined): number {
  const key = (nt ?? "UNKNOWN").toUpperCase();
  return NT_HEX[key] ?? NT_HEX.UNKNOWN;
}

function isWebGLSupported(): boolean {
  if (typeof window === "undefined" || typeof document === "undefined") return false;
  if (typeof navigator !== "undefined" && navigator.userAgent.includes("jsdom")) return false;
  try {
    const probe = document.createElement("canvas");
    return Boolean(probe.getContext("webgl2") || probe.getContext("webgl"));
  } catch {
    return false;
  }
}

interface Node3D {
  source_neuron_id: string;
  neurotransmitter: string | null;
  is_seed: boolean;
  cell_type?: string | null;
  region?: string | null;
  soma_side?: string | null;
  superclass?: string | null;
  pos: THREE.Vector3;
}

interface Connectome3DCanvasProps {
  subgraph: SubgraphResponse;
  theme: "dark" | "light";
  onPivotSeed?: (neuronId: string) => void;
}

const Connectome3DCanvas: React.FC<Connectome3DCanvasProps> = ({
  subgraph,
  theme,
  onPivotSeed,
}) => {
  const { t } = useI18n();
  const mountRef = useRef<HTMLDivElement | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  const [webglOk] = useState<boolean>(isWebGLSupported);
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [flowPulses, setFlowPulses] = useState<boolean>(false);
  const [minSynFilter, setMinSynFilter] = useState<number>(1);
  const [selectedId, setSelectedId] = useState<string | null>(
    subgraph.nodes.find((n) => n.is_seed)?.source_neuron_id ??
      subgraph.nodes[0]?.source_neuron_id ??
      null,
  );
  const [hoveredNode, setHoveredNode] = useState<Node3D | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const autoRotateRef = useRef(autoRotate);
  autoRotateRef.current = autoRotate;
  const flowPulsesRef = useRef(flowPulses);
  flowPulsesRef.current = flowPulses;
  const selectedIdRef = useRef(selectedId);
  selectedIdRef.current = selectedId;

  const maxEdgeCount = useMemo(
    () => Math.max(1, ...subgraph.edges.map((e) => e.synapse_count)),
    [subgraph.edges],
  );

  const layout = useMemo(() => {
    const capped = [...subgraph.nodes].slice(0, 120);
    const seeds = capped
      .filter((n) => n.is_seed)
      .sort((a, b) => a.source_neuron_id.localeCompare(b.source_neuron_id));
    const others = capped
      .filter((n) => !n.is_seed)
      .sort((a, b) => a.source_neuron_id.localeCompare(b.source_neuron_id));

    const nodes3D: Node3D[] = [];
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));

    seeds.forEach((n, idx) => {
      if (seeds.length === 1) {
        nodes3D.push({ ...n, pos: new THREE.Vector3(0, 0, 0) });
      } else {
        const y = 1 - (idx / (seeds.length - 1)) * 2;
        const radius = Math.sqrt(Math.max(0, 1 - y * y));
        const theta = goldenAngle * idx;
        nodes3D.push({
          ...n,
          pos: new THREE.Vector3(
            Math.cos(theta) * radius * 2.4,
            y * 2.1,
            Math.sin(theta) * radius * 2.4,
          ),
        });
      }
    });

    others.forEach((n, idx) => {
      const y = others.length === 1 ? 0 : 1 - (idx / (others.length - 1)) * 2;
      const radiusAtY = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = goldenAngle * idx;
      const shell = idx < 42 ? 7.4 : 11.8;
      // Subtle NT z-bias for clearer inhibitory vs excitatory laminar structure
      const nt = (n.neurotransmitter ?? "UNKNOWN").toUpperCase();
      const yBias = nt === "GABA" ? 1.35 : nt === "ACH" ? -0.9 : 0;
      nodes3D.push({
        ...n,
        pos: new THREE.Vector3(
          Math.cos(theta) * radiusAtY * shell,
          y * shell * 0.85 + yBias,
          Math.sin(theta) * radiusAtY * shell,
        ),
      });
    });

    const nodeMap = new Map<string, Node3D>();
    nodes3D.forEach((n) => nodeMap.set(n.source_neuron_id, n));

    const visibleEdges = subgraph.edges
      .filter(
        (e) =>
          e.synapse_count >= minSynFilter &&
          nodeMap.has(e.pre_neuron_id) &&
          nodeMap.has(e.post_neuron_id),
      )
      .slice(0, 260);

    return { nodes3D, nodeMap, visibleEdges };
  }, [subgraph.nodes, subgraph.edges, minSynFilter]);

  useEffect(() => {
    setSelectedId(
      subgraph.nodes.find((n) => n.is_seed)?.source_neuron_id ??
        subgraph.nodes[0]?.source_neuron_id ??
        null,
    );
  }, [subgraph]);

  useEffect(() => {
    if (!webglOk) return;
    const container = mountRef.current;
    if (!container) return;

    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 380);
    const isDark = theme === "dark";

    const scene = new THREE.Scene();
    const bgColor = isDark ? 0x060b14 : 0xeaf0f8;
    scene.background = new THREE.Color(bgColor);
    scene.fog = new THREE.FogExp2(bgColor, 0.017);

    const camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 200);
    camera.position.set(0, 6.5, 22);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.minDistance = 5;
    controls.maxDistance = 52;
    controls.autoRotate = autoRotateRef.current;
    controls.autoRotateSpeed = 0.65;
    controlsRef.current = controls;

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, isDark ? 0.68 : 0.85));
    const keyLight = new THREE.DirectionalLight(0xe0f2fe, 1.15);
    keyLight.position.set(14, 18, 14);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.55);
    rimLight.position.set(-14, -8, -12);
    scene.add(rimLight);

    const disposables: Array<{ dispose: () => void }> = [];

    // Subtle equatorial reference rings (visual depth frame only)
    for (const r of [7.4, 11.8]) {
      const ringGeo = new THREE.RingGeometry(r - 0.02, r + 0.02, 72);
      const ringMat = new THREE.MeshBasicMaterial({
        color: isDark ? 0x1e293b : 0xcbd5e1,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.45,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      scene.add(ring);
      disposables.push(ringGeo, ringMat);
    }

    // Build soma spheres
    const pickableMeshes: THREE.Mesh[] = [];
    const sphereGeoBase = new THREE.SphereGeometry(0.42, 20, 16);
    const seedGeo = new THREE.SphereGeometry(0.64, 24, 20);
    const haloGeo = new THREE.TorusGeometry(0.92, 0.045, 10, 32);
    const haloMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
    disposables.push(sphereGeoBase, seedGeo, haloGeo, haloMat);

    const nodeMaterials = new Map<string, THREE.MeshStandardMaterial>();
    layout.nodes3D.forEach((node) => {
      const color = ntHex(node.neurotransmitter);
      const mat = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: node.is_seed ? 0.45 : 0.24,
        roughness: 0.32,
        metalness: 0.12,
      });
      disposables.push(mat);
      nodeMaterials.set(node.source_neuron_id, mat);

      const mesh = new THREE.Mesh(node.is_seed ? seedGeo : sphereGeoBase, mat);
      mesh.position.copy(node.pos);
      mesh.userData = { node };
      scene.add(mesh);
      pickableMeshes.push(mesh);

      if (node.is_seed) {
        const halo = new THREE.Mesh(haloGeo, haloMat);
        halo.position.copy(node.pos);
        halo.rotation.x = Math.PI / 2.6;
        scene.add(halo);
      }
    });

    // Build curved synaptic edges + optional schematic flow curves
    const curves: Array<{
      curve: THREE.QuadraticBezierCurve3;
      pre: string;
      post: string;
      color: number;
    }> = [];
    const edgeRecords: Array<{
      pre: string;
      post: string;
      mat: THREE.LineBasicMaterial;
      baseOpacity: number;
    }> = [];

    layout.visibleEdges.forEach((edge, idx) => {
      const src = layout.nodeMap.get(edge.pre_neuron_id);
      const dst = layout.nodeMap.get(edge.post_neuron_id);
      if (!src || !dst) return;

      const mid = new THREE.Vector3().addVectors(src.pos, dst.pos).multiplyScalar(0.5);
      const offsetSign = idx % 2 === 0 ? 1 : -1;
      const dist = src.pos.distanceTo(dst.pos);
      mid.y += offsetSign * Math.min(2.4, dist * 0.14);

      const curve = new THREE.QuadraticBezierCurve3(src.pos, mid, dst.pos);
      const pts = curve.getPoints(18);
      const lineGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const weightRatio = Math.min(1, Math.log1p(edge.synapse_count) / Math.log1p(maxEdgeCount + 4));
      const baseOpacity = 0.24 + weightRatio * 0.56;
      const edgeColor = ntHex(src.neurotransmitter);
      const lineMat = new THREE.LineBasicMaterial({
        color: edgeColor,
        transparent: true,
        opacity: baseOpacity,
      });
      disposables.push(lineGeo, lineMat);
      scene.add(new THREE.Line(lineGeo, lineMat));
      curves.push({ curve, pre: edge.pre_neuron_id, post: edge.post_neuron_id, color: edgeColor });
      edgeRecords.push({
        pre: edge.pre_neuron_id,
        post: edge.post_neuron_id,
        mat: lineMat,
        baseOpacity,
      });
    });

    // Flow pulse spheres (toggled live without tearing down WebGL context)
    const pulseGroup = new THREE.Group();
    const pulseGeo = new THREE.SphereGeometry(0.14, 10, 10);
    disposables.push(pulseGeo);
    const pulseItems = curves.slice(0, 90).map((c, idx) => {
      const mat = new THREE.MeshBasicMaterial({ color: c.color });
      disposables.push(mat);
      const mesh = new THREE.Mesh(pulseGeo, mat);
      pulseGroup.add(mesh);
      return { mesh, curve: c.curve, phase: (idx * 0.13) % 1 };
    });
    scene.add(pulseGroup);

    // Raycaster for hover + click selection
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    const pickAtEvent = (ev: PointerEvent): Node3D | null => {
      const rect = renderer.domElement.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(pickableMeshes, false);
      if (hits.length > 0) {
        return (hits[0].object.userData as { node: Node3D }).node;
      }
      return null;
    };

    const handlePointerMove = (ev: PointerEvent) => {
      const hit = pickAtEvent(ev);
      setHoveredNode(hit);
      renderer.domElement.style.cursor = hit ? "pointer" : "grab";
    };

    const handleClick = (ev: MouseEvent) => {
      const hit = pickAtEvent(ev as unknown as PointerEvent);
      if (hit) {
        setSelectedId(hit.source_neuron_id);
      }
    };

    renderer.domElement.addEventListener("pointermove", handlePointerMove);
    renderer.domElement.addEventListener("click", handleClick);

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.max(entry.contentRect.width, 300);
        const h = Math.max(entry.contentRect.height, 360);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      }
    });
    resizeObserver.observe(container);

    let rafId = 0;
    const clock = new THREE.Clock();

    const animate = () => {
      rafId = window.requestAnimationFrame(animate);
      const dt = clock.getDelta();
      controls.autoRotate = autoRotateRef.current;
      controls.update();

      const sel = selectedIdRef.current;
      nodeMaterials.forEach((mat, nid) => {
        mat.emissiveIntensity = nid === sel ? 0.95 : 0.28;
      });
      edgeRecords.forEach((rec) => {
        const active = sel !== null && (rec.pre === sel || rec.post === sel);
        rec.mat.opacity = sel === null ? rec.baseOpacity : active ? 0.95 : 0.11;
      });

      pulseGroup.visible = flowPulsesRef.current;
      if (flowPulsesRef.current) {
        pulseItems.forEach((p) => {
          p.phase = (p.phase + dt * 0.42) % 1;
          p.curve.getPoint(p.phase, p.mesh.position);
        });
      }

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      window.cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("click", handleClick);
      controls.dispose();
      disposables.forEach((d) => d.dispose());
      renderer.dispose();
    };
  }, [layout, theme, maxEdgeCount, webglOk]);

  const activeNode = useMemo(
    () =>
      (selectedId ? layout.nodeMap.get(selectedId) : undefined) ?? layout.nodes3D[0] ?? null,
    [layout, selectedId],
  );

  const activeDegree = useMemo(() => {
    if (!activeNode) return { inCount: 0, outCount: 0, totalSyn: 0 };
    let inCount = 0;
    let outCount = 0;
    let totalSyn = 0;
    subgraph.edges.forEach((e) => {
      if (e.post_neuron_id === activeNode.source_neuron_id) {
        inCount += 1;
        totalSyn += e.synapse_count;
      }
      if (e.pre_neuron_id === activeNode.source_neuron_id) {
        outCount += 1;
        totalSyn += e.synapse_count;
      }
    });
    return { inCount, outCount, totalSyn };
  }, [activeNode, subgraph.edges]);

  const handleResetCamera = () => {
    const cam = cameraRef.current;
    const ctrl = controlsRef.current;
    if (cam && ctrl) {
      cam.position.set(0, 6.5, 22);
      ctrl.target.set(0, 0, 0);
      ctrl.update();
    }
  };

  const handleCopy = (id: string) => {
    void navigator.clipboard?.writeText(id);
    setCopiedId(id);
    window.setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="viewport-3d-shell">
      <div className="viewport-3d-toolbar">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
          <StatusBadge label={t("topologyDisclaimer")} tone="warn" />
          <div className="subgraph-legend" style={{ marginBottom: 0 }}>
            {Object.entries(NT_CSS).map(([nt, hex]) => (
              <span key={nt} className="legend-swatch">
                <span className="legend-dot" style={{ background: hex }} />
                <span>{nt}</span>
              </span>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: "0.75rem",
              color: "var(--text-secondary)",
            }}
          >
            <span>
              {t("minEdgeFilterLabel")}: <strong>{minSynFilter}</strong>
            </span>
            <input
              type="range"
              min={1}
              max={Math.min(50, maxEdgeCount)}
              value={Math.min(minSynFilter, Math.min(50, maxEdgeCount))}
              onChange={(e) => setMinSynFilter(Number(e.target.value))}
              style={{ width: 90, padding: 0 }}
            />
          </label>
          <button
            type="button"
            className={`btn btn-sm ${autoRotate ? "" : "btn-secondary"}`}
            onClick={() => setAutoRotate((v) => !v)}
          >
            {t("autoRotate")}
          </button>
          <button
            type="button"
            className={`btn btn-sm ${flowPulses ? "" : "btn-secondary"}`}
            title={t("flowDisclaimer")}
            onClick={() => setFlowPulses((v) => !v)}
          >
            {t("flowPulses")}
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleResetCamera}>
            {t("resetCamera")}
          </button>
        </div>
      </div>

      {flowPulses && (
        <div style={{ fontSize: "0.73rem", color: "var(--ruo-text)", marginBottom: 6 }}>
          {t("flowDisclaimer")}
        </div>
      )}

      {!webglOk ? (
        <div className="empty-state">{t("webglUnavailable")}</div>
      ) : (
        <div className="viewport-3d-canvas-wrap">
          <div
            ref={mountRef}
            style={{ width: "100%", height: 420 }}
            aria-label={t("subgraphCanvasTitle")}
          />
          {hoveredNode && (
            <div className="viewport-3d-tooltip">
              <div className="mono" style={{ fontWeight: 700 }}>
                {hoveredNode.source_neuron_id}
              </div>
              <div style={{ fontSize: "0.74rem", color: "var(--text-secondary)" }}>
                {hoveredNode.cell_type ?? hoveredNode.neurotransmitter ?? t("unknown")}
                {hoveredNode.region ? ` · ${hoveredNode.region}` : ""}
              </div>
            </div>
          )}
        </div>
      )}

      {activeNode && (
        <div className="viewport-3d-inspector">
          <div>
            <strong>{t("subgraphNodeInspector")}: </strong>
            <span className="mono">{activeNode.source_neuron_id}</span>{" "}
            <StatusBadge
              label={activeNode.neurotransmitter ?? t("unknown")}
              tone={activeNode.neurotransmitter === "GABA" ? "synth" : "info"}
            />{" "}
            {activeNode.is_seed && <StatusBadge label="SEED" tone="warn" />}
            {activeNode.cell_type && (
              <span style={{ marginLeft: 8, color: "var(--text-secondary)" }}>
                type: <strong>{activeNode.cell_type}</strong>
              </span>
            )}
            {activeNode.soma_side && (
              <span style={{ marginLeft: 8, color: "var(--text-secondary)" }}>
                side: <strong className="mono">{activeNode.soma_side}</strong>
              </span>
            )}
            <span style={{ marginLeft: 10, color: "var(--text-secondary)" }}>
              in: <strong>{activeDegree.inCount}</strong> · out:{" "}
              <strong>{activeDegree.outCount}</strong> · syn:{" "}
              <strong>{activeDegree.totalSyn}</strong>
            </span>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => handleCopy(activeNode.source_neuron_id)}
            >
              {copiedId === activeNode.source_neuron_id ? t("copied") : t("copyId")}
            </button>
            {onPivotSeed && (
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => onPivotSeed(activeNode.source_neuron_id)}
              >
                {t("pivotSubgraph")}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Connectome3DCanvas;
