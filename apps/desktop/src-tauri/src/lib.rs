use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::OnceLock;
use tauri::{Emitter, Manager};
use tokio::io::{AsyncBufReadExt, AsyncReadExt, BufReader};

/// Rodapé anexado ao .exe portátil: [zip][u64 tamanho][u64 magic].
const PORTABLE_MAGIC: u64 = 0x3144_4E42_4F52_5044;
const PORTABLE_FOOTER: u64 = 16;

static RUNTIME_ROOT: OnceLock<PathBuf> = OnceLock::new();
static RUNTIME_ERROR: OnceLock<String> = OnceLock::new();

/// Evita janela de console no Windows ao spawnar python.exe / py.exe.
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

fn hide_console(cmd: &mut Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
}

fn hide_console_tokio(cmd: &mut tokio::process::Command) {
    #[cfg(windows)]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct PreviewInfo {
    title: String,
    thumbnail: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SearchItem {
    title: String,
    url: String,
    thumbnail: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DownloadRequest {
    input: String,
    mode: String,
    profile_id: String,
    output_path: Option<String>,
}

fn project_root() -> PathBuf {
    // Em debug o app usa o repositório. No release, o caminho é resolvido em prepare_runtime.
    if cfg!(debug_assertions) {
        return Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    }
    RUNTIME_ROOT
        .get()
        .cloned()
        .unwrap_or_else(|| exe_dir().join("resources"))
}

fn exe_dir() -> PathBuf {
    std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(|dir| dir.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."))
}

fn runtime_install_dir() -> PathBuf {
    let base = std::env::var("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| exe_dir());
    base.join("Downloader Pro").join("runtime")
}

struct Section<R> {
    inner: R,
    start: u64,
    len: u64,
    pos: u64,
}

impl<R: Read + Seek> Read for Section<R> {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        if self.pos >= self.len {
            return Ok(0);
        }
        let max = ((self.len - self.pos) as usize).min(buf.len());
        self.inner.seek(SeekFrom::Start(self.start + self.pos))?;
        let n = self.inner.read(&mut buf[..max])?;
        self.pos += n as u64;
        Ok(n)
    }
}

impl<R: Read + Seek> Seek for Section<R> {
    fn seek(&mut self, pos: SeekFrom) -> std::io::Result<u64> {
        let next = match pos {
            SeekFrom::Start(offset) => offset as i64,
            SeekFrom::End(offset) => self.len as i64 + offset,
            SeekFrom::Current(offset) => self.pos as i64 + offset,
        };
        if next < 0 {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "seek antes do início do runtime",
            ));
        }
        self.pos = next as u64;
        Ok(self.pos)
    }
}

fn embedded_payload(exe: &Path) -> Option<(u64, u64)> {
    let mut file = File::open(exe).ok()?;
    let size = file.metadata().ok()?.len();
    if size < PORTABLE_FOOTER {
        return None;
    }
    file.seek(SeekFrom::End(-(PORTABLE_FOOTER as i64))).ok()?;
    let mut footer = [0u8; 16];
    file.read_exact(&mut footer).ok()?;
    let zip_len = u64::from_le_bytes(footer[0..8].try_into().ok()?);
    let magic = u64::from_le_bytes(footer[8..16].try_into().ok()?);
    if magic != PORTABLE_MAGIC || zip_len == 0 || zip_len + PORTABLE_FOOTER > size {
        return None;
    }
    Some((size - PORTABLE_FOOTER - zip_len, zip_len))
}

fn extract_payload(exe: &Path, start: u64, len: u64, dest: &Path) -> Result<(), String> {
    let file = File::open(exe).map_err(|e| format!("Não foi possível ler o executável: {e}"))?;
    let section = Section {
        inner: file,
        start,
        len,
        pos: 0,
    };
    let mut archive = zip::ZipArchive::new(section)
        .map_err(|e| format!("Runtime embutido inválido: {e}"))?;
    std::fs::create_dir_all(dest).map_err(|e| format!("Não foi possível criar {dest:?}: {e}"))?;

    for index in 0..archive.len() {
        let mut entry = archive
            .by_index(index)
            .map_err(|e| format!("Falha ao ler o runtime: {e}"))?;
        let Some(rel) = entry.enclosed_name().map(|p| p.to_path_buf()) else {
            continue;
        };
        let out = dest.join(rel);
        if entry.is_dir() {
            std::fs::create_dir_all(&out).map_err(|e| e.to_string())?;
            continue;
        }
        if let Some(parent) = out.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let mut outfile = File::create(&out).map_err(|e| format!("Falha ao gravar {}: {e}", out.display()))?;
        std::io::copy(&mut entry, &mut outfile).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn ensure_extracted(exe: &Path, start: u64, len: u64) -> Result<PathBuf, String> {
    let dest = runtime_install_dir();
    let stamp = dest.join(".payload-stamp");
    let id = format!("{start}:{len}");
    if bridge_script_path(&dest).is_file()
        && std::fs::read_to_string(&stamp).ok().as_deref() == Some(id.as_str())
    {
        return Ok(dest);
    }

    let tmp = dest.with_file_name("runtime.tmp");
    if tmp.exists() {
        std::fs::remove_dir_all(&tmp).map_err(|e| e.to_string())?;
    }
    extract_payload(exe, start, len, &tmp)?;
    if !bridge_script_path(&tmp).is_file() {
        return Err("O executável não contém src/tauri_bridge.py.".into());
    }
    std::fs::write(tmp.join(".payload-stamp"), &id).map_err(|e| e.to_string())?;
    if dest.exists() {
        std::fs::remove_dir_all(&dest).map_err(|e| e.to_string())?;
    }
    std::fs::rename(&tmp, &dest).map_err(|e| format!("Falha ao instalar o runtime: {e}"))?;
    Ok(dest)
}

fn locate_runtime() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| format!("Executável não encontrado: {e}"))?;
    if let Some((start, len)) = embedded_payload(&exe) {
        return ensure_extracted(&exe, start, len);
    }

    let sibling = exe_dir().join("resources");
    if bridge_script_path(&sibling).is_file() {
        return Ok(sibling);
    }
    if bridge_script_path(&exe_dir()).is_file() {
        return Ok(exe_dir());
    }

    Err(
        "Este executável não traz o Python nem os scripts. Copie o arquivo gerado depois do build portátil, não só um .exe antigo."
            .into(),
    )
}

fn prepare_runtime() {
    if cfg!(debug_assertions) {
        return;
    }
    match locate_runtime() {
        Ok(path) => {
            let _ = RUNTIME_ROOT.set(path);
        }
        Err(err) => {
            let _ = RUNTIME_ERROR.set(err);
            let _ = RUNTIME_ROOT.set(exe_dir().join("resources"));
        }
    }
}

fn bridge_missing_message(bridge: &Path) -> String {
    match RUNTIME_ERROR.get() {
        Some(err) => format!("Bridge não encontrado em {}. {err}", bridge.display()),
        None => format!("Bridge não encontrado em {}", bridge.display()),
    }
}

fn bridge_script_path(root: &Path) -> PathBuf {
    root.join("src").join("tauri_bridge.py")
}

fn cookies_path(root: &Path) -> Option<String> {
    let p = root.join("cookies.txt");
    if p.is_file() {
        Some(p.to_string_lossy().into_owned())
    } else {
        None
    }
}

fn parse_progress_line(line: &str) -> Option<Value> {
    let rest = line.rsplit_once("TAURI_PROGRESS:")?.1.trim();
    if let Ok(value) = serde_json::from_str::<Value>(rest) {
        return Some(value);
    }
    let json_start = rest.find('{')?;
    let mut de = serde_json::Deserializer::from_str(&rest[json_start..]);
    Value::deserialize(&mut de).ok()
}

fn command_envs(root: &Path) -> Vec<(&'static str, String)> {
    let mut envs = vec![
        ("PYTHONUNBUFFERED", "1".into()),
        ("PYTHONIOENCODING", "utf-8".into()),
        // Instalação em Program Files não deixa gravar __pycache__ ao lado dos scripts.
        ("PYTHONDONTWRITEBYTECODE", "1".into()),
        ("PYTHONNOUSERSITE", "1".into()),
    ];

    let bin = root.join("bin");
    if bin.is_dir() {
        let current = std::env::var("PATH").unwrap_or_default();
        let sep = if cfg!(windows) { ";" } else { ":" };
        envs.push((
            "PATH",
            format!("{}{}{}", bin.display(), sep, current),
        ));
        let ffmpeg_name = if cfg!(windows) { "ffmpeg.exe" } else { "ffmpeg" };
        let ffmpeg = bin.join(ffmpeg_name);
        if ffmpeg.is_file() {
            envs.push(("FFMPEG_LOCATION", ffmpeg.to_string_lossy().into_owned()));
        }
    }

    envs
}

fn python_candidates() -> &'static [&'static str] {
    if cfg!(target_os = "windows") {
        &["python", "python3", "py"]
    } else {
        &["python3", "python"]
    }
}

fn venv_python_path(root: &Path) -> PathBuf {
    if cfg!(target_os = "windows") {
        root.join(".venv").join("Scripts").join("python.exe")
    } else {
        root.join(".venv").join("bin").join("python3")
    }
}

fn bundled_python_path(root: &Path) -> PathBuf {
    if cfg!(target_os = "windows") {
        root.join("python").join("python.exe")
    } else {
        root.join("python").join("bin").join("python3")
    }
}

fn python_is_available(path: &Path) -> bool {
    let mut cmd = Command::new(path);
    cmd.arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    hide_console(&mut cmd);
    cmd.status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn resolve_python(root: &Path) -> Result<PathBuf, String> {
    let bundled = bundled_python_path(root);
    if bundled.is_file() && python_is_available(&bundled) {
        return Ok(bundled);
    }

    let venv_python = venv_python_path(root);
    if venv_python.is_file() && python_is_available(&venv_python) {
        return Ok(venv_python);
    }

    for name in python_candidates() {
        let mut cmd = Command::new(name);
        if name == &"py" {
            cmd.args(["-3", "-c", "import sys"]);
        } else {
            cmd.arg("--version");
        }
        cmd.stdout(Stdio::null()).stderr(Stdio::null());
        hide_console(&mut cmd);
        let ok = cmd.status().map(|s| s.success()).unwrap_or(false);
        if ok {
            return Ok(PathBuf::from(*name));
        }
    }
    Err(
        "Python não encontrado. No desenvolvimento, crie o .venv na raiz do projeto. No instalador, gere o build de novo para incluir o Python portátil."
            .into(),
    )
}

fn run_python_json(op: &str, payload: Value) -> Result<String, String> {
    let root = project_root();
    let bridge = bridge_script_path(&root);
    if !bridge.is_file() {
        return Err(bridge_missing_message(&bridge));
    }

    let python = resolve_python(&root)?;
    let stdin_str = serde_json::to_string(&payload).map_err(|e| e.to_string())?;

    let mut cmd = Command::new(&python);
    if python.to_string_lossy() == "py" {
        cmd.args(["-3"]);
    }
    cmd.arg(&bridge)
        .arg(op)
        .current_dir(&root)
        .envs(command_envs(&root))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    hide_console(&mut cmd);

    let mut child = cmd.spawn().map_err(|e| {
        format!(
            "Falha ao iniciar Python ({}): {}",
            python.display(), e
        )
    })?;

    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        stdin
            .write_all(stdin_str.as_bytes())
            .map_err(|e| format!("stdin: {}", e))?;
    }

    let output = child.wait_with_output().map_err(|e| e.to_string())?;

    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if err.is_empty() {
            format!("Python saiu com código {:?}", output.status.code())
        } else {
            err
        });
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

#[tauri::command]
fn preview_url(input: String) -> Result<PreviewInfo, String> {
    let root = project_root();
    let mut payload = json!({ "input": input.trim() });
    if let Some(c) = cookies_path(&root) {
        payload
            .as_object_mut()
            .unwrap()
            .insert("cookiesPath".into(), json!(c));
    }

    let raw = run_python_json("preview", payload)?;
    serde_json::from_str::<PreviewInfo>(&raw).map_err(|e| format!("Resposta inválida: {} — {}", e, raw))
}

#[tauri::command]
fn search_youtube(query: String, limit: usize) -> Result<Vec<SearchItem>, String> {
    let root = project_root();
    let lim = if limit == 0 { 5usize } else { limit.min(5) };
    let mut payload = json!({
        "query": query.trim(),
        "limit": lim,
    });
    if let Some(c) = cookies_path(&root) {
        payload
            .as_object_mut()
            .unwrap()
            .insert("cookiesPath".into(), json!(c));
    }

    let raw = run_python_json("search", payload)?;
    serde_json::from_str::<Vec<SearchItem>>(&raw)
        .map_err(|e| format!("Resposta inválida: {} — {}", e, raw))
}

#[tauri::command]
async fn start_download(app: tauri::AppHandle, request: DownloadRequest) -> Result<(), String> {
    if request.input.trim().is_empty() {
        return Err("Input vazio".into());
    }
    if request.mode.trim().is_empty() {
        return Err("Modo vazio".into());
    }
    if request.profile_id.trim().is_empty() {
        return Err("Profile vazio".into());
    }

    let root = project_root();
    let bridge = bridge_script_path(&root);
    if !bridge.is_file() {
        return Err(bridge_missing_message(&bridge));
    }

    let python = resolve_python(&root)?;

    let mut payload = json!({
        "input": request.input.trim(),
        "mode": request.mode.trim().to_lowercase(),
        "profileId": request.profile_id.trim(),
    });
    let obj = payload.as_object_mut().unwrap();
    if let Some(ref p) = request.output_path {
        if !p.trim().is_empty() {
            obj.insert("outputPath".into(), json!(p.trim()));
        }
    }
    if let Some(c) = cookies_path(&root) {
        obj.insert("cookiesPath".into(), json!(c));
    }

    let stdin_str = serde_json::to_string(&payload).map_err(|e| e.to_string())?;

    let mut cmd = tokio::process::Command::new(&python);
    if python.to_string_lossy() == "py" {
        cmd.arg("-3");
    }
    cmd.arg(&bridge)
        .arg("download")
        .current_dir(&root)
        .envs(command_envs(&root))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    hide_console_tokio(&mut cmd);

    let mut child = cmd.spawn().map_err(|e| {
        format!(
            "Falha ao iniciar Python ({}): {}",
            python.display(), e
        )
    })?;

    if let Some(mut stdin) = child.stdin.take() {
        use tokio::io::AsyncWriteExt;
        stdin
            .write_all(stdin_str.as_bytes())
            .await
            .map_err(|e| format!("stdin: {}", e))?;
        stdin.shutdown().await.ok();
    }

    let stderr = child.stderr.take();
    let stdout = child.stdout.take();

    let app_stdout = app.clone();
    let stdout_task = tokio::spawn(async move {
        let Some(stdout) = stdout else {
            return Ok::<(), String>(());
        };
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();
        while let Some(line) = lines.next_line().await.map_err(|e| e.to_string())? {
            let Some(value) = parse_progress_line(&line) else {
                continue;
            };
            app_stdout
                .emit("download-progress", value)
                .map_err(|e| e.to_string())?;
        }
        Ok::<(), String>(())
    });

    let stderr_task = tokio::spawn(async move {
        let mut buf = String::new();
        if let Some(mut s) = stderr {
            let _ = s.read_to_string(&mut buf).await;
        }
        buf
    });

    let status = child.wait().await.map_err(|e| e.to_string())?;

    let stderr_text = stderr_task.await.unwrap_or_default();
    stdout_task
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e)?;

    if !status.success() {
        let msg = stderr_text.trim();
        return Err(if msg.is_empty() {
            format!("Download falhou (código {:?})", status.code())
        } else {
            msg.to_string()
        });
    }

    let _ = app.emit(
        "download-complete",
        json!({ "ok": true }),
    );

    Ok(())
}

#[tauri::command]
fn pick_output_folder(app: tauri::AppHandle) -> Option<String> {
    let window = app.get_webview_window("main")?;
    let folder = tauri_plugin_dialog::DialogExt::dialog(&window).file().blocking_pick_folder()?;
    folder.into_path().ok().map(|p| p.display().to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    prepare_runtime();
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            preview_url,
            search_youtube,
            start_download,
            pick_output_folder
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
