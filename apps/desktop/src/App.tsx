import { FormEvent, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";

type PreviewInfo = {
  title: string;
  thumbnail: string;
};

type SearchItem = {
  title: string;
  url: string;
  thumbnail: string;
};

type DownloadMode = "audio" | "video" | "playlist";
type FormatProfile = "audio_mp3" | "audio_m4a" | "video_mp4" | "video_webm";

type ProgressPayload = {
  kind?: string;
  progress?: number | null;
  percentStr?: string | null;
  speedStr?: string | null;
  etaStr?: string | null;
  title?: string | null;
  playlistIndex?: number | null;
  playlistCount?: number | null;
  mode?: string | null;
};

type DownloadProgressState = {
  percent: number;
  speed: string;
  eta: string;
  title: string;
  done: number;
  total: number;
  logs: string[];
};

function prependUniqueLog(logs: string[], next: string): string[] {
  if (!next) return logs;
  if (logs[0] === next) return logs;
  return [next, ...logs].slice(0, 8);
}

function parsePercent(percentStr?: string | null): number {
  if (!percentStr) return 0;
  const cleaned = percentStr.replace("%", "").trim();
  const num = Number.parseFloat(cleaned);
  return Number.isFinite(num) ? Math.max(0, Math.min(100, Math.round(num))) : 0;
}

const PROFILE_BY_MODE: Record<DownloadMode, FormatProfile> = {
  audio: "audio_mp3",
  video: "video_mp4",
  playlist: "audio_mp3"
};

export default function App() {
  const [inputValue, setInputValue] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [mode, setMode] = useState<DownloadMode>("audio");
  const [status, setStatus] = useState("Pronto");
  const [preview, setPreview] = useState<PreviewInfo | null>(null);
  const [searchResults, setSearchResults] = useState<SearchItem[]>([]);
  const [selectedResultUrl, setSelectedResultUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<DownloadProgressState>({
    percent: 0,
    speed: "",
    eta: "",
    title: "",
    done: 0,
    total: 0,
    logs: []
  });

  const selectedProfile = useMemo(() => PROFILE_BY_MODE[mode], [mode]);

  useEffect(() => {
    let unlistenProgress: (() => void) | undefined;
    let unlistenComplete: (() => void) | undefined;

    listen<ProgressPayload>("download-progress", (event) => {
      const p = event.payload;
      if (p.kind === "started") {
        setIsDownloading(true);
        setDownloadProgress((prev) => ({
          ...prev,
          title: p.title || prev.title,
          logs: prependUniqueLog(prev.logs, "Download iniciado...")
        }));
        setStatus("Download iniciado...");
      } else if (p.kind === "playlist-meta") {
        setDownloadProgress((prev) => ({
          ...prev,
          total: p.playlistCount || prev.total,
          title: p.title || prev.title,
          logs: prependUniqueLog(
            prev.logs,
            `Playlist detectada: ${p.playlistCount || 0} item(ns)`
          )
        }));
      } else if (p.kind === "downloading") {
        const pctValue =
          typeof p.progress === "number"
            ? Math.round(p.progress * 100)
            : parsePercent(p.percentStr);
        const pct = pctValue ? `${pctValue}%` : "";
        const parts = [pct || p.percentStr || "", p.speedStr || "", p.etaStr || ""].filter(
          Boolean
        );
        setDownloadProgress((prev) => ({
          ...prev,
          percent: pctValue,
          speed: p.speedStr || "",
          eta: p.etaStr || "",
          title: p.title || prev.title,
          total: p.playlistCount || prev.total
        }));
        setStatus(parts.join(" · ") || "Baixando...");
      } else if (p.kind === "finished") {
        setDownloadProgress((prev) => {
          const done = p.playlistIndex || prev.done + 1;
          const total = p.playlistCount || prev.total;
          const title = p.title || prev.title || "Item";
          const nextLog = `Concluído ${total ? `${done}/${total}` : done}: ${title}`;
          return {
            ...prev,
            percent: total > 0 ? Math.round((done / total) * 100) : 100,
            done,
            total,
            title,
            logs: prependUniqueLog(prev.logs, nextLog)
          };
        });
        setStatus("Processando arquivo…");
      } else if (p.kind === "post-process") {
        setStatus("Convertendo/processando arquivo...");
      } else if (p.kind === "batch-finished") {
        setDownloadProgress((prev) => ({
          ...prev,
          percent: 100,
          done: prev.total > 0 ? prev.total : Math.max(prev.done, 1),
          logs: prependUniqueLog(prev.logs, "Download finalizado.")
        }));
      } else if (p.kind === "error") {
        setDownloadProgress((prev) => ({
          ...prev,
          logs: prependUniqueLog(prev.logs, "Erro em um item da fila.")
        }));
      }
    }).then((fn) => {
      unlistenProgress = fn;
    });

    listen("download-complete", () => {
      setIsDownloading(false);
      setStatus("Download concluído.");
      setDownloadProgress((prev) => ({
        ...prev,
        percent: 100,
        done: prev.total > 0 ? prev.total : Math.max(prev.done, 1),
        logs: prependUniqueLog(prev.logs, "Download concluído.")
      }));
    }).then((fn) => {
      unlistenComplete = fn;
    });

    return () => {
      unlistenProgress?.();
      unlistenComplete?.();
    };
  }, []);

  async function handlePreview(event: FormEvent) {
    event.preventDefault();

    if (!inputValue.trim()) {
      setStatus("Informe URL ou termo.");
      return;
    }

    setLoading(true);
    setStatus("Carregando preview...");
    try {
      const data = await invoke<PreviewInfo>("preview_url", { input: inputValue.trim() });
      setPreview(data);
      setStatus("Preview carregado.");
    } catch (error) {
      setStatus(`Erro preview: ${String(error)}`);
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }

  function handleInputChange(value: string) {
    setInputValue(value);
    setPreview(null);
    setSearchResults([]);
    setSelectedResultUrl(null);
  }

  async function handleSearch() {
    if (!inputValue.trim()) {
      setStatus("Informe termo para busca.");
      return;
    }

    setLoading(true);
    setIsSearching(true);
    setStatus("Buscando no YouTube...");
    try {
      const data = await invoke<SearchItem[]>("search_youtube", { query: inputValue.trim(), limit: 5 });
      setSearchResults(data);
      setSelectedResultUrl(null);
      setStatus(`${data.length} resultado(s).`);
    } catch (error) {
      setStatus(`Erro busca: ${String(error)}`);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
      setLoading(false);
    }
  }

  async function handleDownload() {
    if (!inputValue.trim()) {
      setStatus("Informe URL ou escolha item da busca.");
      return;
    }

    setLoading(true);
    setIsDownloading(true);
    setStatus("Iniciando download...");
    setDownloadProgress({
      percent: 0,
      speed: "",
      eta: "",
      title: "",
      done: 0,
      total: mode === "playlist" ? 0 : 1,
      logs: []
    });
    try {
      await invoke("start_download", {
        request: {
          input: inputValue.trim(),
          mode,
          profileId: selectedProfile,
          outputPath: outputPath || null
        }
      });
      setStatus("Download concluído.");
      setInputValue("");
      setPreview(null);
      setSearchResults([]);
      setSelectedResultUrl(null);
    } catch (error) {
      setIsDownloading(false);
      setStatus(`Erro download: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  }

  async function pickFolder() {
    try {
      setStatus("Abrindo seletor de pasta...");
      const picked = await open({
        directory: true,
        multiple: false,
        title: "Selecione pasta de saída"
      });
      const path = typeof picked === "string" ? picked : null;
      if (path && path.trim()) {
        setOutputPath(path.trim());
        setStatus(`Pasta selecionada: ${path.trim()}`);
      } else {
        setStatus("Pasta não alterada.");
      }
    } catch (error) {
      setStatus(`Erro pasta: ${String(error)}`);
    }
  }

  return (
    <main className="container">
      <h1>Downloader Pro (Tauri Base)</h1>

      <form onSubmit={handlePreview} className="card top-card">
        <label htmlFor="inputValue">URL YouTube ou termo</label>
        <input
          id="inputValue"
          value={inputValue}
          onChange={(event) => handleInputChange(event.target.value)}
          placeholder="https://youtube.com/... ou nome da música"
        />

        <div className="row">
          <button type="submit" disabled={loading}>Preview</button>
          <button type="button" onClick={handleSearch} disabled={loading}>Buscar (5)</button>
        </div>
        {isSearching && (
          <div className="loading-inline">
            <span className="spinner" /> Pesquisando no YouTube...
          </div>
        )}
      </form>

      <section className="card">
        <h2>Modo</h2>
        <div className="row">
          <button
            type="button"
            className={`mode-button${mode === "audio" ? " active" : ""}`}
            onClick={() => setMode("audio")}
            disabled={loading}
          >
            Audio
          </button>
          <button
            type="button"
            className={`mode-button${mode === "video" ? " active" : ""}`}
            onClick={() => setMode("video")}
            disabled={loading}
          >
            Video
          </button>
          <button
            type="button"
            className={`mode-button${mode === "playlist" ? " active" : ""}`}
            onClick={() => setMode("playlist")}
            disabled={loading}
          >
            Playlist Audio
          </button>
        </div>
        <p>Perfil atual: <code>{selectedProfile}</code></p>
      </section>

      <section className="card">
        <h2>Pasta de saída</h2>
        <div className="row">
          <input value={outputPath} onChange={(event) => setOutputPath(event.target.value)} placeholder="Padrão do sistema" />
          <button type="button" onClick={pickFolder} disabled={loading}>Selecionar</button>
        </div>
      </section>

      <div className="media-grid">
        <section className="card">
          <h2>Preview</h2>
          {preview ? (
            <>
              <p>{preview.title}</p>
              {preview.thumbnail ? (
                <img src={preview.thumbnail} alt={preview.title} className="thumb" />
              ) : (
                <p className="muted">Sem thumbnail para este item.</p>
              )}
            </>
          ) : (
            <p className="muted">Faça preview ou escolha um resultado da busca.</p>
          )}
        </section>

        <section className="card">
          <h2>Resultados</h2>
          {searchResults.length > 0 ? (
            <ul className="results">
              {searchResults.map((item) => (
                <li key={item.url}>
                  <button
                    type="button"
                    className={`result-button${selectedResultUrl === item.url ? " active" : ""}`}
                    onClick={() => {
                      setInputValue(item.url);
                      setPreview({ title: item.title, thumbnail: item.thumbnail });
                      setSelectedResultUrl(item.url);
                    }}
                    disabled={loading}
                  >
                    {item.thumbnail ? (
                      <img src={item.thumbnail} alt={item.title} className="result-thumb" />
                    ) : (
                      <span className="result-thumb placeholder" />
                    )}
                    <span className="result-title">{item.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Sem resultados. Use botão Buscar (5).</p>
          )}
        </section>
      </div>

      <section className="card">
        <button type="button" onClick={handleDownload} disabled={loading}>Baixar</button>
        <p className="status">{status}</p>
        {isDownloading && (
          <div className="loading-inline">
            <span className="spinner" /> Baixando, aguarde...
          </div>
        )}
        <div className="progress-wrap">
          <div className="progress-head">
            <span>{downloadProgress.title || "Sem item em andamento"}</span>
            <span>{downloadProgress.percent}%</span>
          </div>
          <div className="progress-track">
            <div className="progress-bar" style={{ width: `${downloadProgress.percent}%` }} />
          </div>
          <div className="progress-meta">
            <span>{downloadProgress.speed || "-"}</span>
            <span>{downloadProgress.eta ? `ETA ${downloadProgress.eta}` : "-"}</span>
            <span>
              {downloadProgress.total > 0
                ? `${downloadProgress.done}/${downloadProgress.total}`
                : `${downloadProgress.done}`}
            </span>
          </div>
          {downloadProgress.logs.length > 0 && (
            <ul className="progress-logs">
              {downloadProgress.logs.map((log, idx) => (
                <li key={`${log}-${idx}`}>{log}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
