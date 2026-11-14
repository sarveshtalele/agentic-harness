import { health } from "../../lib/health.js";

export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(health());
}
