import { useEffect, useState } from "react";
import { Button, Card, ErrorNote, Field, inputClass, useToast } from "../../components/ui";
import { api } from "../../lib/api";

export function ModelProviderCard() {
  const [llm, setLlm] = useState<any>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [result, setResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const toast = useToast();
  useEffect(() => {
    api("/settings/llm").then((data) => {
      setLlm(data);
      setBaseUrl(data.base_url);
      setModel(data.model);
    });
  }, []);
  const save = async () => {
    setLlm(await api("/settings/llm", { method: "PUT", json: { base_url: baseUrl, model, api_key: apiKey || null } }));
    setApiKey("");
    toast("Model settings saved");
  };
  const test = async () => {
    setTesting(true);
    setResult(await api("/settings/llm/test", { json: { base_url: baseUrl, model, api_key: apiKey || null } }));
    setTesting(false);
  };
  return (
  <Card title="Model provider" id="model-provider">
    <div className="space-y-3">
      <Field label="OpenAI-compatible base URL" hint="OpenAI, Azure OpenAI, LiteLLM, Ollama, or any compatible endpoint."><input name="base-url" className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" /></Field>
      <Field label="Fallback model" hint="Used only when no default is set in the Models list below."><input name="model" className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} /></Field>
      <Field label="API key" hint={llm?.has_api_key ? `A key ending ${llm.api_key_hint} is set. Leave blank to keep it. Keys are encrypted at rest.` : "Keys are encrypted at rest."}><input name="api-key" type="password" autoComplete="off" className={inputClass} value={apiKey} onChange={(e) => setApiKey(e.target.value)} /></Field>
      <div className="flex gap-2"><Button onClick={save}>Save</Button><Button variant="secondary" busy={testing} onClick={test}>Test connection</Button></div>
      {result && (result.ok ? <p className="text-sm text-emerald-600 dark:text-emerald-400" data-testid="llm-ok">Connected to {result.model} in {result.latency_ms} ms. Reply: {result.reply}</p> : <ErrorNote message={result.error} />)}
    </div>
  </Card>
  );
}
