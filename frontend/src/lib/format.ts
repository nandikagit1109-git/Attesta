/** Display helpers. Hashes and addresses always render in the mono font. */

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export function fmtHash(hash: string | null | undefined, keep = 10): string {
  if (!hash) return "";
  if (hash.length <= keep * 2 + 3) return hash;
  return `${hash.slice(0, keep)}...${hash.slice(-keep)}`;
}

export function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}
