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
type Theme = "dark" | "light";

type ProgressPayload = {
  kind?: string;
  progress?: number | null;
  percent?: number | null;
  percentStr?: string | null;
  speedStr?: string | null;
  etaStr?: string | null;
  title?: string | null;
  playlistIndex?: number | null;
  playlistCount?: number | null;
  mode?: string | null;
  attempt?: number | null;
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

type ProfileOption = {
  value: FormatProfile;
  label: string;
};

const PROFILES_BY_MODE: Record<DownloadMode, ProfileOption[]> = {
  audio: [
    { value: "audio_mp3", label: "MP3 — 320 kbps" },
    { value: "audio_m4a", label: "M4A — AAC" }
  ],
  video: [
    { value: "video_mp4", label: "MP4 — H.264" },
    { value: "video_webm", label: "WEBM — VP9" }
  ],
  playlist: [
    { value: "audio_mp3", label: "MP3 — 320 kbps" },
    { value: "audio_m4a", label: "M4A — AAC" }
  ]
};

const THEME_STORAGE_KEY = "downloader-pro-theme";

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
  if (stored === "light" || stored === "dark") return stored;
  const prefersLight = window.matchMedia?.("(prefers-color-scheme: light)").matches;
  return prefersLight ? "light" : "dark";
}

function prependUniqueLog(logs: string[], next: string): string[] {
  if (!next) return logs;
  if (logs[0] === next) return logs;
  return [next, ...logs].slice(0, 8);
}

function stripAnsi(value?: string | null): string {
  if (!value) return "";
  return value.replace(/\u001b\[[0-9;]*m/g, "").trim();
}

function parsePercent(percentStr?: string | null): number {
  const cleaned = stripAnsi(percentStr).replace("%", "").trim();
  const match = cleaned.match(/([\d.]+)/);
  const num = match ? Number.parseFloat(match[1]) : Number.NaN;
  return Number.isFinite(num) ? Math.max(0, Math.min(100, Math.round(num))) : 0;
}

/* ============================================================
   Inline icons (no extra deps)
   ============================================================ */

function IconSearch(props: { size?: number }) {
  const s = props.size ?? 18;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

function IconSun(props: { size?: number }) {
  const s = props.size ?? 18;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function IconMoon(props: { size?: number }) {
  const s = props.size ?? 18;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function IconMusic(props: { size?: number }) {
  const s = props.size ?? 16;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 17V5l12-2v12" />
      <circle cx="6" cy="17" r="3" />
      <circle cx="18" cy="15" r="3" />
    </svg>
  );
}

function IconVideo(props: { size?: number }) {
  const s = props.size ?? 16;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="14" height="12" rx="2" />
      <path d="m22 8-6 4 6 4V8z" />
    </svg>
  );
}

function IconList(props: { size?: number }) {
  const s = props.size ?? 16;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  );
}

function IconFolder(props: { size?: number }) {
  const s = props.size ?? 16;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
    </svg>
  );
}

function IconDownload(props: { size?: number }) {
  const s = props.size ?? 18;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </svg>
  );
}

function IconImage(props: { size?: number }) {
  const s = props.size ?? 28;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="9" cy="9" r="1.5" />
      <path d="m21 15-5-5L5 21" />
    </svg>
  );
}

function IconSparkle(props: { size?: number }) {
  const s = props.size ?? 22;
  return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
    </svg>
  );
}

/* ============================================================
   App
   ============================================================ */

export default function App() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [inputValue, setInputValue] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [mode, setMode] = useState<DownloadMode>("audio");
  const [profile, setProfile] = useState<FormatProfile>("audio_mp3");
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

  const profileOptions = useMemo(() => PROFILES_BY_MODE[mode], [mode]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    if (meta) meta.content = theme === "dark" ? "#0b0f14" : "#f5f7fb";
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    setProfile((current) => {
      const allowed = PROFILES_BY_MODE[mode].map((p) => p.value);
      return allowed.includes(current) ? current : PROFILES_BY_MODE[mode][0].value;
    });
  }, [mode]);

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
      } else if (p.kind === "preparing") {
        setDownloadProgress((prev) => ({
          ...prev,
          title: p.title || prev.title,
          logs: prependUniqueLog(prev.logs, "Preparando download...")
        }));
        setStatus("Preparando download...");
      } else if (p.kind === "retrying") {
        const attempt = p.attempt ? ` (tentativa ${p.attempt})` : "";
        setDownloadProgress((prev) => ({
          ...prev,
          logs: prependUniqueLog(prev.logs, `Tentando outro servidor${attempt}...`)
        }));
        setStatus("Tentando outro servidor do YouTube...");
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
          typeof p.percent === "number"
            ? Math.max(0, Math.min(100, Math.round(p.percent)))
            : typeof p.progress === "number"
              ? Math.round(p.progress * 100)
              : parsePercent(p.percentStr);
        const speed = stripAnsi(p.speedStr);
        const eta = stripAnsi(p.etaStr);
        const pct = `${pctValue}%`;
        const parts = [pct, speed, eta].filter(Boolean);
        setDownloadProgress((prev) => ({
          ...prev,
          percent: pctValue,
          speed,
          eta,
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

  function toggleTheme() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

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
      const data = await invoke<SearchItem[]>("search_youtube", {
        query: inputValue.trim(),
        limit: 5
      });
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
          profileId: profile,
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
    <div className="app">
      <div className="container">
        <header className="topbar">
          <div className="brand">
            <div className="brand-logo">
              <IconDownload size={20} />
            </div>
            <div>
              <h1 className="brand-title">Downloader Pro</h1>
              <p className="brand-sub">YouTube → áudio, vídeo e playlists</p>
            </div>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro"}
            title={theme === "dark" ? "Tema claro" : "Tema escuro"}
          >
            {theme === "dark" ? <IconSun /> : <IconMoon />}
          </button>
        </header>

        <form onSubmit={handlePreview} className="hero">
          <div className="search-field">
            <IconSearch />
            <input
              id="inputValue"
              value={inputValue}
              onChange={(event) => handleInputChange(event.target.value)}
              placeholder="Cole um link do YouTube ou pesquise por título"
              autoComplete="off"
            />
          </div>
          <button type="submit" className="btn" disabled={loading}>
            Preview
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSearch}
            disabled={loading}
          >
            <IconSearch size={16} />
            Buscar
          </button>
        </form>

        {isSearching && (
          <div className="loading-inline" style={{ marginBottom: 12 }}>
            <span className="spinner" /> Pesquisando no YouTube...
          </div>
        )}

        <section className="card">
          <h2 className="card-title">
            <IconSparkle size={14} /> Configuração do download
          </h2>

          <div className="tabs" role="tablist" aria-label="Modo de download">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "audio"}
              className={`tab${mode === "audio" ? " active" : ""}`}
              onClick={() => setMode("audio")}
              disabled={loading}
            >
              <IconMusic /> Áudio
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "video"}
              className={`tab${mode === "video" ? " active" : ""}`}
              onClick={() => setMode("video")}
              disabled={loading}
            >
              <IconVideo /> Vídeo
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "playlist"}
              className={`tab${mode === "playlist" ? " active" : ""}`}
              onClick={() => setMode("playlist")}
              disabled={loading}
            >
              <IconList /> Playlist
            </button>
          </div>

          <div className="config-grid">
            <div className="config-field">
              <label className="field-label" htmlFor="profile-select">
                Formato de saída
              </label>
              <div className="select-wrap">
                <select
                  id="profile-select"
                  value={profile}
                  onChange={(event) => setProfile(event.target.value as FormatProfile)}
                  disabled={loading}
                >
                  {profileOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="config-field">
              <label className="field-label" htmlFor="output-path">
                Pasta de saída
              </label>
              <div className="field-row">
                <input
                  id="output-path"
                  className="field-input"
                  value={outputPath}
                  onChange={(event) => setOutputPath(event.target.value)}
                  placeholder="Padrão: ~/Downloads"
                />
                <button
                  type="button"
                  className="btn btn-icon"
                  onClick={pickFolder}
                  disabled={loading}
                  title="Selecionar pasta"
                  aria-label="Selecionar pasta"
                >
                  <IconFolder />
                </button>
              </div>
            </div>
          </div>
        </section>

        <div className="media-grid">
          <section className="card">
            <h2 className="card-title">
              <IconImage size={14} /> Preview
            </h2>
            {preview ? (
              <div className="preview">
                {preview.thumbnail ? (
                  <img
                    src={preview.thumbnail}
                    alt={preview.title}
                    className="preview-thumb"
                  />
                ) : (
                  <div className="empty-state">
                    <IconImage />
                    <p>Sem thumbnail para este item.</p>
                  </div>
                )}
                <p className="preview-title">{preview.title}</p>
              </div>
            ) : (
              <div className="empty-state">
                <IconImage />
                <p>Faça preview ou escolha um resultado da busca.</p>
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="card-title">
              <IconSearch size={14} /> Resultados
            </h2>
            {searchResults.length > 0 ? (
              <ul className="results">
                {searchResults.map((item) => (
                  <li key={item.url}>
                    <button
                      type="button"
                      className={`result-item${
                        selectedResultUrl === item.url ? " active" : ""
                      }`}
                      onClick={() => {
                        setInputValue(item.url);
                        setPreview({ title: item.title, thumbnail: item.thumbnail });
                        setSelectedResultUrl(item.url);
                      }}
                      disabled={loading}
                    >
                      {item.thumbnail ? (
                        <img
                          src={item.thumbnail}
                          alt={item.title}
                          className="result-thumb"
                        />
                      ) : (
                        <span className="result-thumb placeholder">
                          <IconImage size={18} />
                        </span>
                      )}
                      <span className="result-title">{item.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <IconSearch />
                <p>Sem resultados ainda. Use o botão Buscar acima.</p>
              </div>
            )}
          </section>
        </div>

        <section className="card">
          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={handleDownload}
            disabled={loading}
          >
            <IconDownload /> Baixar agora
          </button>

          <div className="status-line">
            <span className="status-dot" /> {status}
            {isDownloading && (
              <span className="loading-inline" style={{ marginLeft: "auto" }}>
                <span className="spinner" /> Baixando…
              </span>
            )}
          </div>

          <div className="progress">
            <div className="progress-head">
              <span className="progress-title">
                {downloadProgress.title || "Sem item em andamento"}
              </span>
              <span className="progress-percent">{downloadProgress.percent}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-bar"
                style={{ width: `${downloadProgress.percent}%` }}
              />
            </div>
            <div className="progress-meta">
              <span>{downloadProgress.speed || "—"}</span>
              <span>{downloadProgress.eta ? `ETA ${downloadProgress.eta}` : "—"}</span>
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
      </div>
    </div>
  );
}
