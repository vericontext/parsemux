"use client";

import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  Loader2,
  Download,
  Copy,
  Check,
  ChevronDown,
  Key,
  Layers,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  fetchHealth,
  fetchParsers,
  parseDocument,
  compareDocument,
  type ParseResult,
  type ParserInfo,
} from "@/lib/api";
import { ResultView } from "@/components/result-view";
import { MetaPanel } from "@/components/meta-panel";
import { CostPanel } from "@/components/cost-panel";
import { CompareView } from "@/components/compare-view";

type OutputFormat = "markdown" | "text" | "json";

export function ParseWorkspace() {
  const [file, setFile] = useState<File | null>(null);
  const [parsers, setParsers] = useState<ParserInfo[]>([]);
  const [selectedParser, setSelectedParser] = useState("auto");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("markdown");
  const [useLlm, setUseLlm] = useState(false);
  const [llmKey, setLlmKey] = useState("");
  const [extractImages, setExtractImages] = useState(false);
  const [describeImages, setDescribeImages] = useState(false);
  const [useOcr, setUseOcr] = useState(true);
  const [vlmProvider, setVlmProvider] = useState("auto");
  const [showByok, setShowByok] = useState(false);
  const [hasServerKey, setHasServerKey] = useState(false);
  const [limits, setLimits] = useState<{
    max_file_size_mb: number;
    rate_limit_per_min: number;
    max_pages: number;
  } | null>(null);

  const [parsing, setParsing] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<ParseResult | null>(null);
  const [compareResults, setCompareResults] = useState<ParseResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("result");

  // Load parsers, health, and stored BYOK key (retry for Fly.io cold start)
  useEffect(() => {
    let attempts = 0;
    const tryLoad = () => {
      fetchParsers().then(setParsers).catch(() => {});
      fetchHealth()
        .then((h) => {
          setHasServerKey(h.has_server_key);
          setLimits(h.limits);
        })
        .catch(() => {
          attempts++;
          if (attempts < 3) setTimeout(tryLoad, 2000);
        });
    };
    tryLoad();
    const stored = localStorage.getItem("parsemux-llm-key");
    if (stored) setLlmKey(stored);
  }, []);

  // Save BYOK key to localStorage
  useEffect(() => {
    if (llmKey) localStorage.setItem("parsemux-llm-key", llmKey);
    else localStorage.removeItem("parsemux-llm-key");
  }, [llmKey]);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) {
      const f = accepted[0];
      if (limits && f.size > limits.max_file_size_mb * 1024 * 1024) {
        setError(
          `File too large for demo (${limits.max_file_size_mb}MB limit). Install locally for up to 100MB.`
        );
        return;
      }
      setFile(f);
      setResult(null);
      setCompareResults([]);
      setError(null);
    }
  }, [limits]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "text/html": [".html"],
      "text/plain": [".txt"],
      "text/csv": [".csv"],
      "text/markdown": [".md"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/tiff": [".tiff", ".tif"],
    },
  });

  const handleParse = async () => {
    if (!file) return;
    setParsing(true);
    setError(null);
    setResult(null);
    try {
      const res = await parseDocument(file, {
        parser: selectedParser,
        format: outputFormat,
        useLlm,
        llmApiKey: llmKey || undefined,
        extractImages,
        describeImages,
        useOcr,
        vlmProvider: vlmProvider !== "auto" ? vlmProvider : undefined,
        vlmApiKey: llmKey || undefined,
      });
      setResult(res);
      setActiveTab("result");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Parse failed");
    } finally {
      setParsing(false);
    }
  };

  const handleCompare = async () => {
    if (!file) return;
    setComparing(true);
    setError(null);
    setCompareResults([]);
    try {
      const res = await compareDocument(file, llmKey || undefined);
      setCompareResults(res);
      setActiveTab("compare");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Compare failed");
    } finally {
      setComparing(false);
    }
  };

  const availableParsers = parsers.filter((p) => p.available);
  const hasResult = result !== null;
  const hasCompare = compareResults.length > 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Hero section when no result */}
      {!hasResult && !hasCompare && (
        <div className="text-center mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
            Parse any document.{" "}
            <span className="text-amber">Instantly.</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto mb-5">
            Auto-routes to the optimal open-source parser. PDF, DOCX, XLSX, HTML, and 91+ formats. No signup.
          </p>

          {/* Install command */}
          <div className="max-w-lg mx-auto mb-2">
            <div
              className="flex items-center gap-2 bg-muted/50 border border-border rounded-lg px-4 py-2.5 font-mono text-sm cursor-pointer hover:bg-muted transition-colors group"
              onClick={() => {
                navigator.clipboard.writeText(
                  "curl -fsSL https://raw.githubusercontent.com/vericontext/parsemux/main/install.sh | sh"
                );
              }}
              title="Click to copy"
            >
              <span className="text-muted-foreground select-none">$</span>
              <span className="flex-1 text-left truncate">
                curl -fsSL https://raw.githubusercontent.com/vericontext/parsemux/main/install.sh | sh
              </span>
              <Copy className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground shrink-0" />
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5">
              Or try it right here — drop a file below
            </p>
          </div>
        </div>
      )}

      <div className={`grid gap-6 ${hasResult || hasCompare ? "lg:grid-cols-[320px_1fr]" : ""}`}>
        {/* Left panel: Controls */}
        <div className="space-y-4">
          {/* Drop zone */}
          <div
            {...getRootProps()}
            className={`
              relative border-2 border-dashed rounded-xl cursor-pointer
              transition-all duration-200 group
              ${isDragActive ? "drag-active border-amber bg-amber-dim/30" : "border-border hover:border-amber/50 hover:bg-muted/50"}
              ${file ? "p-4" : "p-8 sm:p-12"}
              ${hasResult || hasCompare ? "" : "max-w-2xl mx-auto lg:max-w-none"}
            `}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-amber/10 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-amber" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate text-sm">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} KB · Click or drop to replace
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setResult(null);
                    setCompareResults([]);
                  }}
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            ) : (
              <div className="text-center">
                <Upload className="w-8 h-8 mx-auto mb-3 text-muted-foreground group-hover:text-amber transition-colors" />
                <p className="font-medium mb-1">Drop a document here</p>
                <p className="text-sm text-muted-foreground">
                  PDF, DOCX, XLSX, PPTX, HTML, TXT, images
                </p>
              </div>
            )}
          </div>
          {limits && (
            <p className={`text-[11px] text-muted-foreground text-center mt-1.5 ${hasResult || hasCompare ? "" : "max-w-2xl mx-auto lg:max-w-none"}`}>
              Demo: {limits.max_file_size_mb}MB max · {limits.rate_limit_per_min} req/min ·{" "}
              <a href="https://github.com/vericontext/parsemux#install" className="underline hover:text-foreground" target="_blank" rel="noopener noreferrer">
                Install locally
              </a>{" "}for full access
            </p>
          )}

          {/* Parser selector */}
          <div className={`space-y-3 ${hasResult || hasCompare ? "" : "max-w-2xl mx-auto lg:max-w-none"}`}>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5 block">
                Parser
              </label>
              <div className="flex flex-wrap gap-1.5">
                <ParserChip
                  label="Auto"
                  active={selectedParser === "auto"}
                  onClick={() => setSelectedParser("auto")}
                />
                {availableParsers.map((p) => (
                  <ParserChip
                    key={p.name}
                    label={p.name}
                    active={selectedParser === p.name}
                    onClick={() => setSelectedParser(p.name)}
                    description={p.description}
                  />
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5 block">
                Format
              </label>
              <div className="flex gap-1.5">
                {(["markdown", "text", "json"] as const).map((fmt) => (
                  <button
                    key={fmt}
                    onClick={() => setOutputFormat(fmt)}
                    className={`
                      px-3 py-1.5 text-xs font-mono rounded-md transition-all
                      ${outputFormat === fmt
                        ? "bg-foreground text-background"
                        : "bg-muted text-muted-foreground hover:text-foreground"
                      }
                    `}
                  >
                    {fmt}
                  </button>
                ))}
              </div>
            </div>

            {/* OCR */}
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={useOcr}
                onChange={(e) => setUseOcr(e.target.checked)}
                className="rounded"
              />
              Enable OCR (scanned documents)
            </label>

            {/* Image extraction */}
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={extractImages}
                  onChange={(e) => {
                    setExtractImages(e.target.checked);
                    if (!e.target.checked) setDescribeImages(false);
                  }}
                  className="rounded"
                />
                Extract images
              </label>
              {extractImages && (
                <label className="flex items-center gap-2 text-xs text-muted-foreground ml-4">
                  <input
                    type="checkbox"
                    checked={describeImages}
                    onChange={(e) => setDescribeImages(e.target.checked)}
                    className="rounded"
                  />
                  Describe images with VLM (BYOK)
                </label>
              )}
            </div>

            {/* BYOK collapsible */}
            <div>
              <button
                onClick={() => setShowByok(!showByok)}
                className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                <Key className="w-3 h-3" />
                API Keys (BYOK)
                <ChevronDown className={`w-3 h-3 transition-transform ${showByok ? "rotate-180" : ""}`} />
              </button>
              {showByok && (
                <div className="mt-2 space-y-2">
                  <input
                    type="password"
                    value={llmKey}
                    onChange={(e) => setLlmKey(e.target.value)}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 text-sm font-mono bg-muted border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-amber"
                  />
                  {describeImages && (
                    <div className="flex gap-1.5">
                      {["auto", "openai", "anthropic", "google", "ollama"].map((p) => (
                        <button
                          key={p}
                          onClick={() => setVlmProvider(p)}
                          className={`px-2 py-1 text-[10px] font-mono rounded transition-all ${
                            vlmProvider === p
                              ? "bg-amber text-white"
                              : "bg-muted text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  )}
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={useLlm}
                      onChange={(e) => setUseLlm(e.target.checked)}
                      className="rounded"
                    />
                    Enable LLM-enhanced parsing
                  </label>
                  <p className="text-[10px] text-muted-foreground">
                    {hasServerKey
                      ? "Server has API keys configured. You can override them here, or leave empty to use server keys."
                      : "Stored in your browser only. Never sent to our server."}
                  </p>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-1">
              <Button
                onClick={handleParse}
                disabled={!file || parsing}
                className="flex-1 bg-amber hover:bg-amber/90 text-white font-medium"
              >
                {parsing ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Layers className="w-4 h-4 mr-2" />
                )}
                {parsing ? "Parsing..." : "Parse"}
              </Button>
              <Button
                variant="outline"
                onClick={handleCompare}
                disabled={!file || comparing}
                className="shrink-0"
              >
                {comparing ? <Loader2 className="w-4 h-4 animate-spin" /> : "Compare"}
              </Button>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Right panel: Results */}
        {(hasResult || hasCompare) && (
          <div className="min-w-0">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <div className="flex items-center justify-between mb-4">
                <TabsList>
                  <TabsTrigger value="result" disabled={!hasResult}>
                    Result
                  </TabsTrigger>
                  <TabsTrigger value="raw" disabled={!hasResult}>
                    Raw
                  </TabsTrigger>
                  <TabsTrigger value="compare" disabled={!hasCompare}>
                    Compare
                  </TabsTrigger>
                </TabsList>
                {hasResult && <ResultActions content={result!.content} fileName={file?.name} />}
              </div>

              <TabsContent value="result" className="mt-0">
                {result && (
                  <div className="space-y-4">
                    <div className="border border-border rounded-xl bg-card p-6 min-h-[300px] max-h-[600px] overflow-y-auto">
                      <ResultView content={result.content} format={outputFormat} result={result} />
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <MetaPanel result={result} />
                      {result.cost_estimate && <CostPanel cost={result.cost_estimate} />}
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="raw" className="mt-0">
                {result && (
                  <pre className="border border-border rounded-xl bg-card p-6 font-mono text-sm overflow-auto max-h-[600px] whitespace-pre-wrap break-words">
                    {result.content}
                  </pre>
                )}
              </TabsContent>

              <TabsContent value="compare" className="mt-0">
                {hasCompare && <CompareView results={compareResults} />}
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  );
}

function ParserChip({
  label,
  active,
  onClick,
  description,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  description?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={description}
      className={`
        px-3 py-1.5 text-xs font-mono rounded-md transition-all
        ${active
          ? "bg-amber text-white shadow-sm"
          : "bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80"
        }
      `}
    >
      {label}
    </button>
  );
}

function ResultActions({
  content,
  fileName,
}: {
  content: string;
  fileName?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(fileName || "output").replace(/\.[^.]+$/, "")}_parsed.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex gap-1">
      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCopy}>
        {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
      </Button>
      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleDownload}>
        <Download className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
}
