/*
 * Portable Responses reference client.
 * Authority: reusable artifact, NOT API schema.
 * Truth sources: upstream/openapi/openapi.yaml + upstream/docs/*
 * No UI, Android, Termux, Kali, local-shell, database, or framework assumptions.
 */

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: any };

export interface FunctionToolDefinition {
  type: "function";
  name: string;
  description?: string;
  parameters: JsonObject;
  strict?: boolean;
  defer_loading?: boolean;
}

export interface FunctionCallItem {
  type: "function_call";
  call_id: string;
  name: string;
  arguments: string;
  [key: string]: any;
}

export interface RegisteredFunctionTool {
  definition: FunctionToolDefinition;
  execute: (args: JsonObject, call: FunctionCallItem) => Promise<unknown> | unknown;
}

export interface ResponsesClientConfig {
  apiKey: string;
  baseUrl?: string;
  model?: string;
  maxFunctionRounds?: number;
  headers?: Record<string, string>;
  fetch?: typeof globalThis.fetch;
}

export interface RunOptions {
  model?: string;
  instructions?: string;
  tools?: JsonObject[];
  reasoning?: JsonObject;
  request?: JsonObject;
  maxFunctionRounds?: number;
}

export interface StreamOptions extends RunOptions {
  onEvent?: (event: JsonObject) => void;
}

function requireValue(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function asOutputString(value: unknown): string {
  if (typeof value === "string") return value;
  const encoded = JSON.stringify(value);
  return encoded === undefined ? String(value) : encoded;
}

export class OpenAICodexResponses {
  readonly baseUrl: string;
  readonly model: string;
  private readonly apiKey: string;
  private readonly maxFunctionRounds: number;
  private readonly extraHeaders: Record<string, string>;
  private readonly fetchImpl: typeof globalThis.fetch;
  private readonly functions = new Map<string, RegisteredFunctionTool>();

  constructor(config: ResponsesClientConfig) {
    requireValue(config.apiKey?.trim(), "OpenAI API credential is required.");
    this.apiKey = config.apiKey;
    this.baseUrl = (config.baseUrl ?? "https://api.openai.com/v1").replace(/\/$/, "");
    this.model = config.model ?? "gpt-5.6-sol";
    this.maxFunctionRounds = config.maxFunctionRounds ?? 16;
    this.extraHeaders = { ...(config.headers ?? {}) };
    this.fetchImpl = config.fetch ?? globalThis.fetch;
    requireValue(typeof this.fetchImpl === "function", "A fetch implementation is required.");
  }

  registerFunction(tool: RegisteredFunctionTool): this {
    requireValue(tool.definition.type === "function", "Only custom function definitions may be registered for caller execution.");
    requireValue(tool.definition.name?.trim(), "Function tool name is required.");
    requireValue(!this.functions.has(tool.definition.name), `Function tool '${tool.definition.name}' is already registered.`);
    this.functions.set(tool.definition.name, tool);
    return this;
  }

  unregisterFunction(name: string): boolean {
    return this.functions.delete(name);
  }

  registeredFunctionDefinitions(): FunctionToolDefinition[] {
    return [...this.functions.values()].map((entry) => structuredClone(entry.definition));
  }

  async create(body: JsonObject): Promise<JsonObject> {
    requireValue(body && typeof body === "object", "Responses request body is required.");
    const response = await this.fetchImpl(`${this.baseUrl}/responses`, {
      method: "POST",
      headers: this.headers("application/json"),
      body: JSON.stringify(body),
    });
    const text = await response.text();
    if (!response.ok) throw new Error(`OpenAI Responses HTTP ${response.status}: ${text}`);
    requireValue(text.trim(), "OpenAI Responses returned an empty body.");
    return JSON.parse(text) as JsonObject;
  }

  async stream(body: JsonObject, onEvent: (event: JsonObject) => void = () => {}): Promise<JsonObject> {
    const response = await this.fetchImpl(`${this.baseUrl}/responses`, {
      method: "POST",
      headers: this.headers("application/json", "text/event-stream"),
      body: JSON.stringify({ ...body, stream: true }),
    });
    if (!response.ok) throw new Error(`OpenAI Responses HTTP ${response.status}: ${await response.text()}`);
    requireValue(response.body, "Streaming response has no body.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    let completed: JsonObject | null = null;
    let terminalError: string | null = null;

    const consumeLine = (line: string): void => {
      if (!line.startsWith("data:")) return;
      const data = line.slice(5).trim();
      if (!data || data === "[DONE]") return;
      const event = JSON.parse(data) as JsonObject;
      onEvent(event);
      if (event.type === "response.completed" && event.response) completed = event.response;
      if (event.type === "response.failed") terminalError = event.response?.error?.message ?? data;
      if (event.type === "error") terminalError = event.message ?? event.error?.message ?? data;
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      pending += decoder.decode(value, { stream: true });
      let newline: number;
      while ((newline = pending.indexOf("\n")) >= 0) {
        consumeLine(pending.slice(0, newline).replace(/\r$/, ""));
        pending = pending.slice(newline + 1);
      }
    }
    pending += decoder.decode();
    if (pending.trim()) consumeLine(pending.replace(/\r$/, ""));
    if (terminalError) throw new Error(`OpenAI Responses stream failed: ${terminalError}`);
    requireValue(completed, "Responses stream ended without response.completed.");
    return completed;
  }

  async run(input: JsonValue, options: RunOptions = {}): Promise<JsonObject> {
    const tools = [...(options.tools ?? []), ...this.registeredFunctionDefinitions()];
    const base: JsonObject = {
      model: options.model ?? this.model,
      input,
      ...(options.instructions !== undefined ? { instructions: options.instructions } : {}),
      ...(options.reasoning !== undefined ? { reasoning: options.reasoning } : {}),
      ...(tools.length ? { tools } : {}),
      ...(options.request ?? {}),
    };

    let response = await this.create(base);
    const maxRounds = options.maxFunctionRounds ?? this.maxFunctionRounds;

    for (let round = 0; round < maxRounds; round += 1) {
      const calls = this.functionCalls(response);
      if (calls.length === 0) return response;
      requireValue(response.id, "Function-call response omitted response.id required for continuation.");

      const outputs = await Promise.all(calls.map(async (call) => {
        const registration = this.functions.get(call.name);
        requireValue(registration, `No executor registered for custom function '${call.name}'.`);
        let args: JsonObject;
        try {
          args = JSON.parse(call.arguments || "{}") as JsonObject;
        } catch (error) {
          throw new Error(`Invalid arguments JSON for '${call.name}': ${(error as Error).message}`);
        }
        const result = await registration.execute(args, call);
        return { type: "function_call_output", call_id: call.call_id, output: asOutputString(result) };
      }));

      response = await this.create({
        ...base,
        input: outputs,
        previous_response_id: response.id,
      });
    }

    throw new Error(`Function-call continuation exceeded ${maxRounds} rounds without a terminal response.`);
  }

  async runStreamed(input: JsonValue, options: StreamOptions = {}): Promise<JsonObject> {
    const tools = [...(options.tools ?? []), ...this.registeredFunctionDefinitions()];
    const body: JsonObject = {
      model: options.model ?? this.model,
      input,
      ...(options.instructions !== undefined ? { instructions: options.instructions } : {}),
      ...(options.reasoning !== undefined ? { reasoning: options.reasoning } : {}),
      ...(tools.length ? { tools } : {}),
      ...(options.request ?? {}),
    };
    return this.stream(body, options.onEvent);
  }

  functionCalls(response: JsonObject): FunctionCallItem[] {
    const output = Array.isArray(response?.output) ? response.output : [];
    return output.filter((item: any) => item?.type === "function_call") as FunctionCallItem[];
  }

  outputText(response: JsonObject): string {
    if (typeof response?.output_text === "string") return response.output_text;
    const chunks: string[] = [];
    for (const item of Array.isArray(response?.output) ? response.output : []) {
      if (item?.type !== "message" || !Array.isArray(item.content)) continue;
      for (const part of item.content) if (part?.type === "output_text" && typeof part.text === "string") chunks.push(part.text);
    }
    return chunks.join("");
  }

  private headers(contentType: string, accept = "application/json"): Record<string, string> {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      "Content-Type": contentType,
      Accept: accept,
      ...this.extraHeaders,
    };
  }
}

export default OpenAICodexResponses;
