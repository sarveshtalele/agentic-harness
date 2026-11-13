export type Tool = { name: string; description: string; input_schema: any };
export type Server = {
  id: string; name: string; transport: string; command: string | null; args: string[]; url: string | null;
  status: "not_connected" | "connected" | "error"; error_message: string | null; last_connected_at: string | null; tools_listed_at: string | null;
  plugin_id: string | null; secret_names: string[]; auth?: string; tools: Tool[]; tools_count: number;
};
export type Template = { id: string; name: string; transport: string; command?: string; args?: string[]; url?: string; env_names?: string[]; header_names?: string[]; description: string };
export type Grant = { id: string; server_id: string; tool_name: string; role: string };
export type Row = { key: string; value: string };
