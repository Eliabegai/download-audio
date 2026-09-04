use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tauri::{Emitter, Manager};
use tokio::io::{AsyncBufReadExt, AsyncReadExt, BufReader};

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
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..")
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

fn python_env() -> [(&'static str, &'static str); 2] {
    [("PYTHONUNBUFFERED", "1"), ("PYTHONIOENCODING", "utf-8")]
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
        "Python não encontrado. Crie o ambiente com: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
            .into(),
    )
}

fn run_python_json(op: &str, payload: Value) -> Result<String, String> {
    let root = project_root();
    let bridge = bridge_script_path(&root);
    if !bridge.is_file() {
        return Err(format!(
            "Bridge não encontrado em {}",
            bridge.display()
        ));
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
        .envs(python_env())
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
        return Err(format!(
            "Bridge não encontrado em {}",
            bridge.display()
        ));
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
        .envs(python_env())
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
