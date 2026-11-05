import fs from "fs";
import path from "path";
import { AgentSession } from "../core/AgentSession";
import { SessionState, HarnessMode } from "../types";

/**
 * DeepSeek-Inspired Session Store & Persistence
 * Persists AgentSession states as JSON files to enable multi-turn continuity,
 * branch isolation, and instant session restore across restarts.
 */
export class SessionStore {
  private baseDir: string;

  constructor(baseDir?: string) {
    this.baseDir = baseDir || path.join(process.cwd(), ".sessions");
    this.ensureDirExists();
  }

  private ensureDirExists(): void {
    if (!fs.existsSync(this.baseDir)) {
      try {
        fs.mkdirSync(this.baseDir, { recursive: true });
      } catch (e) {
        console.error("Failed to create sessions directory:", e);
      }
    }
  }

  public listSessions(): Array<{
    id: string;
    name: string;
    mode: HarnessMode;
    activeAgentId: string;
    messagesCount: number;
    todosCount: number;
    updatedAt: number;
    createdAt: number;
  }> {
    this.ensureDirExists();
    try {
      const files = fs.readdirSync(this.baseDir).filter((f) => f.endsWith(".json"));
      const list = files
        .map((f) => {
          try {
            const raw = fs.readFileSync(path.join(this.baseDir, f), "utf-8");
            const data: SessionState = JSON.parse(raw);
            return {
              id: data.id,
              name: data.name,
              mode: data.mode,
              activeAgentId: data.activeAgentId,
              messagesCount: data.messages ? data.messages.length : 0,
              todosCount: data.todos ? data.todos.length : 0,
              updatedAt: data.updatedAt || Date.now(),
              createdAt: data.createdAt || Date.now(),
            };
          } catch {
            return null;
          }
        })
        .filter((item): item is NonNullable<typeof item> => item !== null)
        .sort((a, b) => b.updatedAt - a.updatedAt);

      return list;
    } catch {
      return [];
    }
  }

  public getSession(id: string): AgentSession | null {
    this.ensureDirExists();
    const filePath = path.join(this.baseDir, `${id}.json`);
    if (!fs.existsSync(filePath)) {
      return null;
    }

    try {
      const raw = fs.readFileSync(filePath, "utf-8");
      const state: SessionState = JSON.parse(raw);
      return AgentSession.fromJSON(state);
    } catch (e) {
      console.error(`Failed to read session file ${filePath}:`, e);
      return null;
    }
  }

  public saveSession(session: AgentSession): void {
    this.ensureDirExists();
    const filePath = path.join(this.baseDir, `${session.getId()}.json`);
    try {
      const state = session.getState();
      fs.writeFileSync(filePath, JSON.stringify(state, null, 2), "utf-8");
    } catch (e) {
      console.error(`Failed to persist session ${session.getId()}:`, e);
    }
  }

  public deleteSession(id: string): boolean {
    this.ensureDirExists();
    const filePath = path.join(this.baseDir, `${id}.json`);
    if (fs.existsSync(filePath)) {
      try {
        fs.unlinkSync(filePath);
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }

  public createSession(name?: string, mode: HarnessMode = "plan"): AgentSession {
    const session = new AgentSession({
      name: name || `QE Session #${this.listSessions().length + 1}`,
      mode,
    });
    this.saveSession(session);
    return session;
  }
}
