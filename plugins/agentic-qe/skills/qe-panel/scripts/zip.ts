// Minimal ZIP writer (deflate, UTF-8 names, no ZIP64): standard library only.
import { crc32, deflateRawSync } from "node:zlib";

export interface ZipEntry { name: string; data: Uint8Array; mtime?: Date }

const dosTime = (d: Date) => ((d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1)) & 0xffff;
const dosDate = (d: Date) => ((Math.max(0, d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()) & 0xffff;

/** Archive path: relative, forward slashes, no "..", no NUL. */
export const safeName = (n: string): boolean => !!n && !n.startsWith("/") && !/^[A-Za-z]:/.test(n) && !n.includes("\0") && !n.includes("\\") && !n.split("/").includes("..");

export function buildZip(entries: ZipEntry[]): Buffer {
  if (entries.length > 0xffff) throw new Error("too many files for a plain ZIP");
  const parts: Buffer[] = [], central: Buffer[] = [];
  let offset = 0;
  for (const e of entries) {
    if (!safeName(e.name)) throw new Error(`refusing unsafe zip path: ${e.name}`);
    const raw = Buffer.from(e.data), name = Buffer.from(e.name, "utf-8");
    const packed = raw.length ? deflateRawSync(raw) : raw;
    const method = raw.length ? 8 : 0, crc = crc32(raw), d = e.mtime ?? new Date();
    if (raw.length > 0xffffffff || offset > 0xffffffff) throw new Error("zip too large for a plain ZIP");
    const head = Buffer.alloc(30);
    head.writeUInt32LE(0x04034b50, 0); head.writeUInt16LE(20, 4); head.writeUInt16LE(0x0800, 6); head.writeUInt16LE(method, 8);
    head.writeUInt16LE(dosTime(d), 10); head.writeUInt16LE(dosDate(d), 12); head.writeUInt32LE(crc, 14);
    head.writeUInt32LE(packed.length, 18); head.writeUInt32LE(raw.length, 22); head.writeUInt16LE(name.length, 26);
    const cen = Buffer.alloc(46);
    cen.writeUInt32LE(0x02014b50, 0); cen.writeUInt16LE(20, 4); cen.writeUInt16LE(20, 6); cen.writeUInt16LE(0x0800, 8); cen.writeUInt16LE(method, 10);
    cen.writeUInt16LE(dosTime(d), 12); cen.writeUInt16LE(dosDate(d), 14); cen.writeUInt32LE(crc, 16);
    cen.writeUInt32LE(packed.length, 20); cen.writeUInt32LE(raw.length, 24); cen.writeUInt16LE(name.length, 28); cen.writeUInt32LE(offset, 42);
    parts.push(head, name, packed);
    central.push(cen, name);
    offset += 30 + name.length + packed.length;
  }
  const cd = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...parts, cd, end]);
}
