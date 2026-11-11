import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export function synthesizeMockUser(role: "admin" | "customer" | "viewer" = "customer", isValid: boolean = true) {
  if (!isValid) {
    return {
      id: "invalid-id",
      email: "not-an-email",
      role: "unauthorized-role"
    };
  }
  return {
    id: `usr_${role}_001`,
    email: `testuser_${role}@example.com`,
    role
  };
}

/**
 * Generates repetitive edge and boundary datasets (strings, numbers, payloads).
 */
export function synthesizeBoundaryPayload(type: "string" | "number" | "json") {
  switch (type) {
    case "string":
      return {
        empty: "",
        whitespaceOnly: "   \t\n  ",
        maxLength1024: "A".repeat(1024),
        specialCharacters: "<script>alert('xss')</script>' OR 1=1; -- 🚀 漢字",
        unicodeEmoji: "🔥💻🧪🎯✨"
      };
    case "number":
      return {
        zero: 0,
        negativeOne: -1,
        minSafeInteger: Number.MIN_SAFE_INTEGER,
        maxSafeInteger: Number.MAX_SAFE_INTEGER,
        floatingPointPrecision: 0.1 + 0.2
      };
    case "json":
      return {
        emptyObject: {},
        emptyArray: [],
        deeplyNested: { l1: { l2: { l3: { l4: { value: "deep" } } } } },
        nullFields: { name: null, count: null }
      };
  }
}

/**
 * Generates deterministic synthetic pagination slices.
 */
export function synthesizeMockPagination<T>(items: T[], pageSize: number = 10, pageIndex: number = 0) {
  const startIndex = pageIndex * pageSize;
  const endIndex = startIndex + pageSize;
  const pageItems = items.slice(startIndex, endIndex);
  const totalPages = Math.ceil(items.length / pageSize);

  return {
    items: pageItems,
    pageIndex,
    pageSize,
    totalItems: items.length,
    totalPages,
    hasNextPage: pageIndex < totalPages - 1,
    hasPrevPage: pageIndex > 0
  };
}

/**
 * Generates standard HTTP headers for testing authentication boundaries.
 */
export function synthesizeAuthHeaders(role: string = "customer", isValid: boolean = true): Record<string, string> {
  if (!isValid) {
    return {
      "Authorization": "Bearer invalid_or_expired_token",
      "X-User-Role": "anonymous",
      "Content-Type": "application/json"
    };
  }
  return {
    "Authorization": `Bearer mock_jwt_token_for_${role}`,
    "X-User-Role": role,
    "Content-Type": "application/json"
  };
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

// CLI: node synthesize-data.ts <spec.json> -> JSON
// spec: {"kind":"user","role":"admin","valid":true} | {"kind":"boundary","type":"string|number|json"}
//     | {"kind":"pagination","items":[...],"pageSize":10,"pageIndex":0} | {"kind":"auth","role":"customer","valid":true}
if (isCli) {
  const file = process.argv[2];
  if (!file) { console.error("usage: node synthesize-data.ts <spec.json>"); process.exit(2); }
  const s = JSON.parse(readFileSync(file, "utf-8"));
  const out = s.kind === "user" ? synthesizeMockUser(s.role, s.valid ?? true)
    : s.kind === "boundary" ? synthesizeBoundaryPayload(s.type)
    : s.kind === "pagination" ? synthesizeMockPagination(s.items ?? [], s.pageSize, s.pageIndex)
    : s.kind === "auth" ? synthesizeAuthHeaders(s.role, s.valid ?? true)
    : null;
  if (out === null) { console.error(`unknown kind '${s.kind}'`); process.exit(2); }
  console.log(JSON.stringify(out, null, 2));
}
