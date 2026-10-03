/**
 * Typed shapes for every Attesta API response the frontend consumes.
 * Field names mirror the backend serializers in backend/app/schemas.py.
 */

export type Role = "student" | "issuer" | "recruiter";

export type TrustState =
  | "AI-extracted (unverified)"
  | "Issuer-verified"
  | "Revoked"
  | "Tampered"
  | "Unknown";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  org_name: string;
  headline: string;
  wallet_address: string;
  public_fields: Record<string, boolean>;
  created_at: string | null;
}

export interface AuthPayload {
  token: string;
  user: User;
}

export interface AgentRun {
  id: string;
  agent: string;
  input_summary: string;
  output: Record<string, unknown>;
  confidence: number;
  flags: string[];
  duration_ms: number;
  used_fallback: boolean;
  created_at: string | null;
}

export interface ExtractedSkill {
  id: string;
  name?: string;
  category?: string;
  confidence?: number;
  verified: boolean;
  [key: string]: unknown;
}

export interface Credential {
  id: string;
  chain_credential_id: number;
  evidence_id: string;
  issuer_id: string;
  issuer_name: string;
  issuer_org: string;
  recipient_address: string;
  doc_hash: string;
  tx_hash: string;
  block_number: number;
  revoked: boolean;
  revoked_at: string | null;
  revoke_reason: string | null;
  issued_at: string | null;
}

export interface Evidence {
  id: string;
  title: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  sha256: string;
  trust_state: TrustState;
  extracted: {
    title?: string;
    issuer?: string;
    student_name?: string;
    date?: string;
    credential_id?: string;
    skills?: ExtractedSkill[];
    confidence?: number;
    flags?: string[];
    warnings?: string[];
  };
  skills: ExtractedSkill[];
  student: { id: string; full_name: string } | null;
  credential: Credential | null;
  has_tampered_copy: boolean;
  created_at: string | null;
  agent_runs?: AgentRun[];
}

export interface VerifyCandidate {
  credential_id: string;
  state: TrustState;
  reason: string;
  presented_hash: string;
  onchain_hash: string | null;
  hash_match: boolean;
  issuer_address: string;
  recipient_address: string;
  block_number: number;
  tx_hash: string;
  issued_at: string | null;
  revoked: boolean;
  revoked_at: string | null;
  revoke_reason: string;
  evidence_title: string;
}

export interface VerifyResult extends VerifyCandidate {
  candidates: VerifyCandidate[];
}

export interface GraphNode {
  id: string;
  kind: "evidence" | "skill" | "project";
  label: string;
  trust_state?: TrustState;
  category?: string;
  verified: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  kind: string;
  strength: number;
}

export interface SkillGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RoleInfo {
  id: string;
  title: string;
  description: string;
}

export interface RolesResponse {
  roles: RoleInfo[];
  default: string | null;
}

export interface SkillRef {
  skill_id: string;
  weight: number;
  verified?: boolean;
  priority?: string;
}

export interface CareerGap {
  role: { id: string; title: string };
  score: number;
  matched: SkillRef[];
  missing: SkillRef[];
  unverified: SkillRef[];
  project_ideas: string[];
  reasoning: string;
}

export interface JobMatch {
  score: number;
  matched: SkillRef[];
  missing: SkillRef[];
  unverified: SkillRef[];
  required_count: number;
  reasoning: string;
  run_id: string;
}

export interface DirectoryEntry {
  user_id: string;
  wallet_address: string;
  full_name?: string;
  headline?: string;
  email?: string;
  skills?: { verified: string[]; unverified: string[] };
}

export interface PublicProfile {
  user_id: string;
  role: Role;
  org_name: string;
  wallet_address: string;
  summary: string;
  full_name?: string;
  headline?: string;
  email?: string;
  skills?: { verified: string[]; unverified: string[] };
  projects?: { id: string; title: string; description: string; skills: string[] }[];
  credentials?: { id: string; title: string; revoked: boolean; trust_state: TrustState }[];
}

export interface AuditEntry {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  object_type: string;
  object_id: string;
  detail: Record<string, unknown>;
  created_at: string | null;
}

export interface ChainInfo {
  chain_id: number;
  rpc_url: string;
  contract_address: string;
  deployed: boolean;
  explorer_url: string;
}

export interface BulkRow {
  student_email: string;
  status: "issued" | "error";
  evidence_id?: string;
  credential_id?: string;
  tx_hash?: string;
  error?: string;
}

export interface Project {
  id: string;
  title: string;
  description: string;
  skills: string[];
  created_at: string | null;
}
