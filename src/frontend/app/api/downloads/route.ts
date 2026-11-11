// Desktop installers for the login page, read from the Blob `downloads` container's latest.json (docs/DESKTOP_RELEASE_GUIDE.md).
// Public by design: it only relays a public manifest. Nothing is listed that the manifest does not name.
type Listed = { name: string; os: string; arch: string; kind: string; size: number; sha256: string };

const SAFE_NAME = /^[\w .()+-]{1,200}\.(dmg|zip|msi)$/;

function clean(file: any): Listed | null {
  if (!file || typeof file.name !== "string" || !SAFE_NAME.test(file.name)) return null;
  if (!/^[0-9a-f]{64}$/.test(String(file.sha256)) || !Number.isFinite(file.size)) return null;
  return { name: file.name, os: String(file.os), arch: String(file.arch), kind: String(file.kind), size: Number(file.size), sha256: String(file.sha256) };
}

export async function GET() {
  const base = (process.env.ATLAS_DOWNLOADS_URL || "").replace(/\/+$/, "");
  if (!/^https?:\/\//.test(base)) return Response.json({ configured: false, files: [] });
  try {
    const response = await fetch(`${base}/latest.json`, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (!response.ok) return Response.json({ configured: true, files: [], error: `latest.json answered HTTP ${response.status}` });
    const manifest = await response.json();
    const files = (Array.isArray(manifest?.files) ? manifest.files : []).map(clean).filter(Boolean) as Listed[];
    return Response.json({ configured: true, version: String(manifest?.version || ""), files: files.map((f) => ({ ...f, url: `${base}/${encodeURIComponent(f.name)}` })) });
  } catch (error: any) {
    return Response.json({ configured: true, files: [], error: `Could not read latest.json: ${error?.name || "error"}` });
  }
}
