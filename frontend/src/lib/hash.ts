/** Browser-side hashing (feature 1): the file never leaves the machine. */

export async function sha256File(file: File | Blob): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return toHex(new Uint8Array(digest));
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Character mask for the side-by-side hash comparison: true where the two
 * hex strings differ (positions beyond the shorter string also count).
 */
export function hashDiffMask(a: string, b: string): boolean[] {
  const len = Math.max(a.length, b.length);
  const mask: boolean[] = [];
  for (let i = 0; i < len; i++) mask.push(a[i] !== b[i]);
  return mask;
}
