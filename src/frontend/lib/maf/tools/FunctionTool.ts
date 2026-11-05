import { ToolDefinition, ExecutionContext } from "../types";

/**
 * MAF FunctionTool Abstraction (agent-framework.pdf pp. 210-235)
 */
export class FunctionTool implements ToolDefinition {
  public name: string;
  public description: string;
  public parameters: {
    type: "object";
    properties: Record<string, any>;
    required?: string[];
  };
  public requiresApproval?: boolean;
  public gateNumber?: number;
  private executeFn: (args: any, context: ExecutionContext) => Promise<any>;

  constructor(options: {
    name: string;
    description: string;
    parameters: {
      type: "object";
      properties: Record<string, any>;
      required?: string[];
    };
    requiresApproval?: boolean;
    gateNumber?: number;
    execute: (args: any, context: ExecutionContext) => Promise<any>;
  }) {
    this.name = options.name;
    this.description = options.description;
    this.parameters = options.parameters;
    this.requiresApproval = options.requiresApproval ?? false;
    this.gateNumber = options.gateNumber;
    this.executeFn = options.execute;
  }

  public async execute(args: any, context: ExecutionContext): Promise<any> {
    return this.executeFn(args, context);
  }
}
