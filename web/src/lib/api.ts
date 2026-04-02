const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ExtractedImage {
  data_b64: string;
  format: string;
  width: number | null;
  height: number | null;
  page_number: number | null;
  description: string | null;
  description_model: string | null;
}

export interface CostEstimate {
  parsemux_cost_usd: number;
  cloud_costs: Record<string, number>;
  savings_vs_cheapest_cloud: number;
  page_count: number;
  vlm_cost_usd: number;
  vlm_images_described: number;
}

export interface ParseResult {
  content: string;
  parser_used: string;
  metadata: Record<string, unknown>;
  confidence: number | null;
  elapsed_ms: number;
  cost_estimate: CostEstimate | null;
  images: ExtractedImage[];
}

export interface ParserInfo {
  name: string;
  available: boolean;
  supported_mimes: string[];
  description: string;
  requires_gpu: boolean;
  requires_llm_key: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  parsers_available: number;
  has_server_key: boolean;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/v1/health`);
  if (!res.ok) throw new Error("API not reachable");
  return res.json();
}

export async function fetchParsers(): Promise<ParserInfo[]> {
  const res = await fetch(`${API_BASE}/v1/parsers`);
  if (!res.ok) throw new Error("Failed to fetch parsers");
  return res.json();
}

export async function parseDocument(
  file: File,
  options: {
    parser?: string;
    format?: string;
    useLlm?: boolean;
    llmApiKey?: string;
    extractImages?: boolean;
    describeImages?: boolean;
    vlmProvider?: string;
    vlmApiKey?: string;
  } = {}
): Promise<ParseResult> {
  const params = new URLSearchParams();
  if (options.parser && options.parser !== "auto") params.set("parser", options.parser);
  if (options.format) params.set("format", options.format);
  if (options.useLlm) params.set("use_llm", "true");
  if (options.extractImages) params.set("extract_images", "true");
  if (options.describeImages) params.set("describe_images", "true");
  if (options.vlmProvider) params.set("vlm_provider", options.vlmProvider);

  const formData = new FormData();
  formData.append("file", file);

  const headers: Record<string, string> = {};
  if (options.llmApiKey) headers["X-LLM-API-Key"] = options.llmApiKey;
  if (options.vlmApiKey) headers["X-VLM-API-Key"] = options.vlmApiKey;

  const res = await fetch(`${API_BASE}/v1/parse?${params}`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Parse failed: ${text}`);
  }
  return res.json();
}

export async function compareDocument(
  file: File,
  llmApiKey?: string
): Promise<ParseResult[]> {
  const formData = new FormData();
  formData.append("file", file);

  const headers: Record<string, string> = {};
  if (llmApiKey) headers["X-LLM-API-Key"] = llmApiKey;

  const res = await fetch(`${API_BASE}/v1/parse/compare`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Compare failed: ${text}`);
  }
  return res.json();
}
