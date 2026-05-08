import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
function prependUniqueLog(logs, next) {
    if (!next)
        return logs;
    if (logs[0] === next)
        return logs;
    return [next, ...logs].slice(0, 8);
}
function parsePercent(percentStr) {
    if (!percentStr)
        return 0;
    const cleaned = percentStr.replace("%", "").trim();
    const num = Number.parseFloat(cleaned);
    return Number.isFinite(num) ? Math.max(0, Math.min(100, Math.round(num))) : 0;
}
const PROFILE_BY_MODE = {
    audio: "audio_mp3",
    video: "video_mp4",
    playlist: "audio_mp3"
};
export default function App() {
    const [inputValue, setInputValue] = useState("");
    const [outputPath, setOutputPath] = useState("");
    const [mode, setMode] = useState("audio");
    const [status, setStatus] = useState("Pronto");
    const [preview, setPreview] = useState(null);
    const [searchResults, setSearchResults] = useState([]);
    const [selectedResultUrl, setSelectedResultUrl] = useState(null);
    const [loading, setLoading] = useState(false);
    const [isSearching, setIsSearching] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState({
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
        let unlistenProgress;
        let unlistenComplete;
        listen("download-progress", (event) => {
            const p = event.payload;
            if (p.kind === "started") {
                setIsDownloading(true);
                setDownloadProgress((prev) => ({
                    ...prev,
                    title: p.title || prev.title,
                    logs: prependUniqueLog(prev.logs, "Download iniciado...")
                }));
                setStatus("Download iniciado...");
            }
            else if (p.kind === "playlist-meta") {
                setDownloadProgress((prev) => ({
                    ...prev,
                    total: p.playlistCount || prev.total,
                    title: p.title || prev.title,
                    logs: prependUniqueLog(prev.logs, `Playlist detectada: ${p.playlistCount || 0} item(ns)`)
                }));
            }
            else if (p.kind === "downloading") {
                const pctValue = typeof p.progress === "number"
                    ? Math.round(p.progress * 100)
                    : parsePercent(p.percentStr);
                const pct = pctValue ? `${pctValue}%` : "";
                const parts = [pct || p.percentStr || "", p.speedStr || "", p.etaStr || ""].filter(Boolean);
                setDownloadProgress((prev) => ({
                    ...prev,
                    percent: pctValue,
                    speed: p.speedStr || "",
                    eta: p.etaStr || "",
                    title: p.title || prev.title,
                    total: p.playlistCount || prev.total
                }));
                setStatus(parts.join(" · ") || "Baixando...");
            }
            else if (p.kind === "finished") {
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
            }
            else if (p.kind === "post-process") {
                setStatus("Convertendo/processando arquivo...");
            }
            else if (p.kind === "batch-finished") {
                setDownloadProgress((prev) => ({
                    ...prev,
                    percent: 100,
                    done: prev.total > 0 ? prev.total : Math.max(prev.done, 1),
                    logs: prependUniqueLog(prev.logs, "Download finalizado.")
                }));
            }
            else if (p.kind === "error") {
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
    async function handlePreview(event) {
        event.preventDefault();
        if (!inputValue.trim()) {
            setStatus("Informe URL ou termo.");
            return;
        }
        setLoading(true);
        setStatus("Carregando preview...");
        try {
            const data = await invoke("preview_url", { input: inputValue.trim() });
            setPreview(data);
            setStatus("Preview carregado.");
        }
        catch (error) {
            setStatus(`Erro preview: ${String(error)}`);
            setPreview(null);
        }
        finally {
            setLoading(false);
        }
    }
    function handleInputChange(value) {
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
            const data = await invoke("search_youtube", { query: inputValue.trim(), limit: 5 });
            setSearchResults(data);
            setSelectedResultUrl(null);
            setStatus(`${data.length} resultado(s).`);
        }
        catch (error) {
            setStatus(`Erro busca: ${String(error)}`);
            setSearchResults([]);
        }
        finally {
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
        }
        catch (error) {
            setIsDownloading(false);
            setStatus(`Erro download: ${String(error)}`);
        }
        finally {
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
            }
            else {
                setStatus("Pasta não alterada.");
            }
        }
        catch (error) {
            setStatus(`Erro pasta: ${String(error)}`);
        }
    }
    return (_jsxs("main", { className: "container", children: [_jsx("h1", { children: "Downloader Pro (Tauri Base)" }), _jsxs("form", { onSubmit: handlePreview, className: "card top-card", children: [_jsx("label", { htmlFor: "inputValue", children: "URL YouTube ou termo" }), _jsx("input", { id: "inputValue", value: inputValue, onChange: (event) => handleInputChange(event.target.value), placeholder: "https://youtube.com/... ou nome da m\u00FAsica" }), _jsxs("div", { className: "row", children: [_jsx("button", { type: "submit", disabled: loading, children: "Preview" }), _jsx("button", { type: "button", onClick: handleSearch, disabled: loading, children: "Buscar (5)" })] }), isSearching && (_jsxs("div", { className: "loading-inline", children: [_jsx("span", { className: "spinner" }), " Pesquisando no YouTube..."] }))] }), _jsxs("section", { className: "card", children: [_jsx("h2", { children: "Modo" }), _jsxs("div", { className: "row", children: [_jsx("button", { type: "button", className: `mode-button${mode === "audio" ? " active" : ""}`, onClick: () => setMode("audio"), disabled: loading, children: "Audio" }), _jsx("button", { type: "button", className: `mode-button${mode === "video" ? " active" : ""}`, onClick: () => setMode("video"), disabled: loading, children: "Video" }), _jsx("button", { type: "button", className: `mode-button${mode === "playlist" ? " active" : ""}`, onClick: () => setMode("playlist"), disabled: loading, children: "Playlist Audio" })] }), _jsxs("p", { children: ["Perfil atual: ", _jsx("code", { children: selectedProfile })] })] }), _jsxs("section", { className: "card", children: [_jsx("h2", { children: "Pasta de sa\u00EDda" }), _jsxs("div", { className: "row", children: [_jsx("input", { value: outputPath, onChange: (event) => setOutputPath(event.target.value), placeholder: "Padr\u00E3o do sistema" }), _jsx("button", { type: "button", onClick: pickFolder, disabled: loading, children: "Selecionar" })] })] }), _jsxs("div", { className: "media-grid", children: [_jsxs("section", { className: "card", children: [_jsx("h2", { children: "Preview" }), preview ? (_jsxs(_Fragment, { children: [_jsx("p", { children: preview.title }), preview.thumbnail ? (_jsx("img", { src: preview.thumbnail, alt: preview.title, className: "thumb" })) : (_jsx("p", { className: "muted", children: "Sem thumbnail para este item." }))] })) : (_jsx("p", { className: "muted", children: "Fa\u00E7a preview ou escolha um resultado da busca." }))] }), _jsxs("section", { className: "card", children: [_jsx("h2", { children: "Resultados" }), searchResults.length > 0 ? (_jsx("ul", { className: "results", children: searchResults.map((item) => (_jsx("li", { children: _jsxs("button", { type: "button", className: `result-button${selectedResultUrl === item.url ? " active" : ""}`, onClick: () => {
                                            setInputValue(item.url);
                                            setPreview({ title: item.title, thumbnail: item.thumbnail });
                                            setSelectedResultUrl(item.url);
                                        }, disabled: loading, children: [item.thumbnail ? (_jsx("img", { src: item.thumbnail, alt: item.title, className: "result-thumb" })) : (_jsx("span", { className: "result-thumb placeholder" })), _jsx("span", { className: "result-title", children: item.title })] }) }, item.url))) })) : (_jsx("p", { className: "muted", children: "Sem resultados. Use bot\u00E3o Buscar (5)." }))] })] }), _jsxs("section", { className: "card", children: [_jsx("button", { type: "button", onClick: handleDownload, disabled: loading, children: "Baixar" }), _jsx("p", { className: "status", children: status }), isDownloading && (_jsxs("div", { className: "loading-inline", children: [_jsx("span", { className: "spinner" }), " Baixando, aguarde..."] })), _jsxs("div", { className: "progress-wrap", children: [_jsxs("div", { className: "progress-head", children: [_jsx("span", { children: downloadProgress.title || "Sem item em andamento" }), _jsxs("span", { children: [downloadProgress.percent, "%"] })] }), _jsx("div", { className: "progress-track", children: _jsx("div", { className: "progress-bar", style: { width: `${downloadProgress.percent}%` } }) }), _jsxs("div", { className: "progress-meta", children: [_jsx("span", { children: downloadProgress.speed || "-" }), _jsx("span", { children: downloadProgress.eta ? `ETA ${downloadProgress.eta}` : "-" }), _jsx("span", { children: downloadProgress.total > 0
                                            ? `${downloadProgress.done}/${downloadProgress.total}`
                                            : `${downloadProgress.done}` })] }), downloadProgress.logs.length > 0 && (_jsx("ul", { className: "progress-logs", children: downloadProgress.logs.map((log, idx) => (_jsx("li", { children: log }, `${log}-${idx}`))) }))] })] })] }));
}
