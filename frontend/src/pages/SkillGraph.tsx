import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ReactFlow, Controls, Handle, Position } from "@xyflow/react";
import type { Edge, Node, NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { apiGet } from "../lib/api";
import type { SkillGraph as SkillGraphData } from "../lib/types";

/**
 * Feature 6: the skill graph. Verified and unverified nodes differ by border
 * style and an explicit label, never by color alone.
 */

type FlowData = { label: string; sub: string; verified: boolean; kind: string };

function BaseNode({ data }: NodeProps) {
  const d = data as FlowData;
  const border = d.verified
    ? "border-[2.5px] border-double border-ink"
    : "border border-dashed border-ink";
  return (
    <div className={`bg-surface px-3 py-2 ${border}`} style={{ minWidth: 140 }}>
      <Handle type="target" position={Position.Left} style={{ background: "#2E1F14", width: 6, height: 6, borderRadius: 0 }} />
      <p className="text-xs leading-4">{d.label}</p>
      <p className="text-[10px] uppercase tracking-wide mt-0.5">{d.sub}</p>
      <Handle type="source" position={Position.Right} style={{ background: "#2E1F14", width: 6, height: 6, borderRadius: 0 }} />
    </div>
  );
}

const nodeTypes = { attesta: BaseNode };

export default function SkillGraphPage() {
  const [graph, setGraph] = useState<SkillGraphData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<SkillGraphData>("/api/skills/graph")
      .then(setGraph)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [] as Node[], edges: [] as Edge[] };
    const ns: Node[] = [];
    const es: Edge[] = [];
    let evidenceRow = 0;
    let skillRow = 0;
    let projectRow = 0;
    for (const n of graph.nodes) {
      if (n.kind === "evidence") {
        ns.push({
          id: n.id,
          type: "attesta",
          position: { x: 0, y: evidenceRow++ * 110 },
          data: { label: n.label, sub: n.trust_state ?? "evidence", verified: n.verified, kind: n.kind },
        });
      } else if (n.kind === "skill") {
        ns.push({
          id: n.id,
          type: "attesta",
          position: { x: 340, y: skillRow++ * 90 },
          data: {
            label: n.label,
            sub: `${n.verified ? "verified" : "unverified"}${n.category ? ` · ${n.category}` : ""}`,
            verified: n.verified,
            kind: n.kind,
          },
        });
      } else {
        ns.push({
          id: n.id,
          type: "attesta",
          position: { x: 680, y: projectRow++ * 110 },
          data: { label: n.label, sub: "project · unverified", verified: false, kind: n.kind },
        });
      }
    }
    for (const e of graph.edges) {
      es.push({
        id: `${e.from}->${e.to}`,
        source: e.from,
        target: e.to,
        label: `strength ${e.strength.toFixed(2)}`,
      });
    }
    return { nodes: ns, edges: es };
  }, [graph]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-3">
        <h1 className="font-display text-3xl font-semibold">Skill graph</h1>
        <p className="mt-3 text-sm leading-relaxed">
          Each certificate feeds skills; projects add unverified skills of your own. A skill turns
          verified when an issuer anchors a matching certificate on-chain.
        </p>
        <div className="mt-4 border border-ink p-3 text-xs space-y-2">
          <p>
            <span className="inline-block w-4 border-t-[2.5px] border-double border-ink align-middle mr-2" />
            double border + "verified" label
          </p>
          <p>
            <span className="inline-block w-4 border-t border-dashed border-ink align-middle mr-2" />
            dashed border + "unverified" label
          </p>
          <p>States never rely on color alone.</p>
        </div>
        <div className="mt-4 flex flex-col gap-2 text-xs">
          <Link to="/career" className="underline underline-offset-4">
            See the career gap for these skills
          </Link>
        </div>
        {error && <p className="mt-4 text-sm text-rust">{error}</p>}
      </section>

      <section className="lg:col-span-9">
        <div className="border border-ink h-[560px]">
          {!graph ? (
            <p className="p-4 text-sm">Loading</p>
          ) : nodes.length === 0 ? (
            <p className="p-4 text-sm">
              No evidence yet. Upload a certificate and the graph builds itself.
            </p>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Controls showInteractive={false} />
            </ReactFlow>
          )}
        </div>
      </section>
    </div>
  );
}
