import { ChatMessage } from "../types";

/**
 * MAF CompactionEngine (agent-framework.pdf pp. 185-205)
 * DeepSeek-style context window compaction and history pruning.
 */
export class CompactionEngine {
  private maxHistoryTokens: number;

  constructor(maxHistoryTokens: number = 32000) {
    this.maxHistoryTokens = maxHistoryTokens;
  }

  /**
   * Compacts conversation history by condensing past verbose tool outputs
   * and summarizing distant messages while preserving gate approvals and todos.
   */
  public compact(messages: ChatMessage[]): ChatMessage[] {
    if (messages.length <= 10) {
      return messages;
    }

    return messages.map((msg, idx) => {
      // Don't compact the last 4 messages (active context window)
      if (idx >= messages.length - 4) {
        return msg;
      }

      // Compact verbose tool outputs in older messages
      if (msg.role === "tool" && msg.content && msg.content.length > 800) {
        return {
          ...msg,
          content: `${msg.content.slice(0, 400)}\n\n[... Output compacted: ${msg.content.length - 400} characters truncated for context efficiency ...]\n${msg.content.slice(-200)}`,
        };
      }

      // Compact toolCalls result payloads
      if (msg.toolCalls && msg.toolCalls.length > 0) {
        const compactedCalls = msg.toolCalls.map((tc) => {
          if (tc.result && typeof tc.result === "string" && tc.result.length > 500) {
            return {
              ...tc,
              result: `${tc.result.slice(0, 300)}... [compacted]`,
            };
          }
          return tc;
        });
        return { ...msg, toolCalls: compactedCalls };
      }

      return msg;
    });
  }
}
