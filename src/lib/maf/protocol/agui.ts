import { AGUIEvent } from "../types";

/**
 * MAF AG-UI Protocol Serializer & Streamer (agent-framework.pdf pp. 510-545)
 * Formats events into Server-Sent Events (SSE) data frames for real-time Next.js UI consumption.
 */
export class AGUIProtocolHandler {
  /**
   * Serializes an AGUIEvent into an SSE wire format chunk: "data: {...}\n\n"
   */
  public static serializeEvent(event: AGUIEvent): string {
    return `data: ${JSON.stringify(event)}\n\n`;
  }

  /**
   * Encodes a stream response headers for SSE streaming in Next.js App Router.
   */
  public static getSSEHeaders(): HeadersInit {
    return {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    };
  }

  /**
   * Parses an SSE data frame back into an AGUIEvent on the client side.
   */
  public static parseEvent(dataLine: string): AGUIEvent | null {
    try {
      const trimmed = dataLine.trim();
      if (!trimmed.startsWith("data:")) {
        return null;
      }
      const jsonStr = trimmed.replace(/^data:\s*/, "");
      return JSON.parse(jsonStr) as AGUIEvent;
    } catch {
      return null;
    }
  }
}
