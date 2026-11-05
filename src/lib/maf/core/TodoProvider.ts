import { TodoItem, ToolDefinition, ExecutionContext } from "../types";

/**
 * MAF TodoProvider (agent-framework.pdf pp. 90-105)
 * Manages active execution checklist for multi-step agentic workflows.
 */
export class TodoProvider {
  /**
   * Generates MAF-compliant tool definitions for Todo management.
   */
  public getTools(): ToolDefinition[] {
    return [
      {
        name: "todos_add",
        description: "Add one or more tasks to the active Harness Todo checklist.",
        parameters: {
          type: "object",
          properties: {
            tasks: {
              type: "array",
              items: { type: "string" },
              description: "Array of task descriptions to add to the todo list",
            },
          },
          required: ["tasks"],
        },
        execute: async (args: { tasks: string[] }, context: ExecutionContext) => {
          const newTodos: TodoItem[] = args.tasks.map((taskTitle) => ({
            id: `todo-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
            title: taskTitle,
            status: "pending",
            createdAt: Date.now(),
            agentId: context.agentId,
          }));

          const updatedTodos = [...context.session.todos, ...newTodos];
          await context.updateSession({ todos: updatedTodos });
          await context.emitEvent({
            type: "STATE_DELTA",
            delta: { todos: updatedTodos },
          });

          return {
            success: true,
            addedCount: newTodos.length,
            todos: newTodos,
          };
        },
      },
      {
        name: "todos_complete",
        description: "Mark one or more tasks in the Todo checklist as completed.",
        parameters: {
          type: "object",
          properties: {
            ids: {
              type: "array",
              items: { type: "string" },
              description: "Array of todo IDs or task title substrings to mark as completed",
            },
          },
          required: ["ids"],
        },
        execute: async (args: { ids: string[] }, context: ExecutionContext) => {
          const completedIds = new Set(args.ids);
          const updatedTodos = context.session.todos.map((todo) => {
            const matchesId = completedIds.has(todo.id);
            const matchesTitle = args.ids.some((query) =>
              todo.title.toLowerCase().includes(query.toLowerCase())
            );
            if (matchesId || matchesTitle) {
              return {
                ...todo,
                status: "completed" as const,
                completedAt: Date.now(),
              };
            }
            return todo;
          });

          await context.updateSession({ todos: updatedTodos });
          await context.emitEvent({
            type: "STATE_DELTA",
            delta: { todos: updatedTodos },
          });

          return {
            success: true,
            completedCount: updatedTodos.filter((t) => t.status === "completed").length,
            totalTodos: updatedTodos.length,
          };
        },
      },
      {
        name: "todos_list",
        description: "Retrieve all current tasks in the active Harness Todo checklist.",
        parameters: {
          type: "object",
          properties: {},
        },
        execute: async (_args: any, context: ExecutionContext) => {
          return {
            todos: context.session.todos,
            summary: {
              total: context.session.todos.length,
              pending: context.session.todos.filter((t) => t.status === "pending").length,
              completed: context.session.todos.filter((t) => t.status === "completed").length,
            },
          };
        },
      },
      {
        name: "todos_update",
        description: "Update the status or title of a specific todo item.",
        parameters: {
          type: "object",
          properties: {
            id: { type: "string", description: "The ID of the todo to update" },
            status: {
              type: "string",
              enum: ["pending", "in_progress", "completed", "failed"],
            },
            title: { type: "string", description: "Optional new title for the todo" },
          },
          required: ["id", "status"],
        },
        execute: async (
          args: { id: string; status: "pending" | "in_progress" | "completed" | "failed"; title?: string },
          context: ExecutionContext
        ) => {
          const updatedTodos = context.session.todos.map((todo) => {
            if (todo.id === args.id) {
              return {
                ...todo,
                status: args.status,
                title: args.title || todo.title,
                completedAt: args.status === "completed" ? Date.now() : undefined,
              };
            }
            return todo;
          });

          await context.updateSession({ todos: updatedTodos });
          await context.emitEvent({
            type: "STATE_DELTA",
            delta: { todos: updatedTodos },
          });

          return { success: true, updatedId: args.id, status: args.status };
        },
      },
    ];
  }
}
