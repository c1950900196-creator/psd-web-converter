from __future__ import annotations

import argparse
import html
import json
import mimetypes
import shutil
import tempfile
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlparse

from .cli import VALID_MODES, convert_one


APP_ROOT = Path.home() / ".psd-web-converter"
UPLOAD_ROOT = APP_ROOT / "uploads"
OUTPUT_ROOT = APP_ROOT / "outputs"
MAX_UPLOAD_SIZE = 512 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动 PSD Web Converter 本地 Web UI。")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=8787, help="监听端口，默认 8787")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), WebHandler)
    print(f"PSD Web Converter 已启动：http://{args.host}:{args.port}")
    server.serve_forever()


class WebHandler(BaseHTTPRequestHandler):
    server_version = "PSDWebConverter/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_home())
            return
        if parsed.path.startswith("/preview/"):
            self._serve_preview(parsed.path)
            return
        if parsed.path.startswith("/download/"):
            self._serve_download(parsed.path)
            return
        self._send_text("Not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/convert":
            self._send_text("Not found", HTTPStatus.NOT_FOUND)
            return

        try:
            result = self._handle_convert()
        except Exception as exc:
            self._send_html(render_home(error=f"{exc.__class__.__name__}: {exc}"), HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if result["ok"]:
            self._send_html(render_result(result))
        else:
            self._send_html(render_home(error=result["error"]), HTTPStatus.BAD_REQUEST)

    def _handle_convert(self) -> dict:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return {"ok": False, "error": "请用表单上传 PSD 文件。"}

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {"ok": False, "error": "上传内容为空。"}
        if length > MAX_UPLOAD_SIZE:
            return {"ok": False, "error": "PSD 文件过大，当前限制 512MB。"}

        raw_body = self.rfile.read(length)
        fields, files = parse_multipart(content_type, raw_body)
        mode = fields.get("mode", "editable")
        if mode not in VALID_MODES:
            mode = "editable"

        uploaded = files.get("psd")
        if not uploaded or not uploaded["filename"].lower().endswith(".psd"):
            return {"ok": False, "error": "请上传 .psd 文件。"}

        job_id = uuid.uuid4().hex[:12]
        upload_dir = UPLOAD_ROOT / job_id
        output_dir = OUTPUT_ROOT / job_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        psd_path = upload_dir / safe_filename(uploaded["filename"])
        psd_path.write_bytes(uploaded["content"])

        args = SimpleNamespace(mode=mode, force=True, batch=False)
        code = convert_one(psd_path, output_dir, args)
        if code != 0:
            report = output_dir / "report.md"
            detail = report.read_text(encoding="utf-8") if report.exists() else "转换失败，请确认本机 Photoshop 可用。"
            return {"ok": False, "error": detail}

        return {
            "ok": True,
            "job_id": job_id,
            "mode": mode,
            "filename": psd_path.name,
            "output_dir": str(output_dir),
            "report": read_text(output_dir / "report.md"),
        }

    def _serve_preview(self, path: str) -> None:
        parts = [unquote(part) for part in path.split("/") if part]
        if len(parts) < 2:
            self._send_text("Not found", HTTPStatus.NOT_FOUND)
            return
        job_id = parts[1]
        rel = Path(*parts[2:]) if len(parts) > 2 else Path("index.html")
        target = safe_join(OUTPUT_ROOT / job_id, rel)
        if not target or not target.exists() or not target.is_file():
            self._send_text("Not found", HTTPStatus.NOT_FOUND)
            return
        self._send_file(target)

    def _serve_download(self, path: str) -> None:
        job_id = path.rstrip("/").split("/")[-1]
        source = OUTPUT_ROOT / job_id
        if not source.exists():
            self._send_text("Not found", HTTPStatus.NOT_FOUND)
            return
        archive_base = Path(tempfile.gettempdir()) / f"psd-web-converter-{job_id}"
        archive = shutil.make_archive(str(archive_base), "zip", source)
        self._send_file(Path(archive), download_name=f"{job_id}-output.zip")

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _send_text(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _send_file(self, path: Path, download_name: str | None = None) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        with path.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)


def parse_multipart(content_type: str, body: bytes) -> tuple[dict[str, str], dict[str, dict]]:
    marker = "boundary="
    if marker not in content_type:
        return {}, {}
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    delimiter = ("--" + boundary).encode()
    fields: dict[str, str] = {}
    files: dict[str, dict] = {}

    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        headers = raw_headers.decode("utf-8", errors="ignore")
        disposition = next((line for line in headers.split("\r\n") if line.lower().startswith("content-disposition")), "")
        attrs = parse_disposition_attrs(disposition)
        name = attrs.get("name")
        if not name:
            continue
        content = content.rstrip(b"\r\n")
        if "filename" in attrs:
            files[name] = {"filename": attrs.get("filename") or "upload.psd", "content": content}
        else:
            fields[name] = content.decode("utf-8", errors="ignore")
    return fields, files


def parse_disposition_attrs(value: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for item in value.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        key, raw = item.split("=", 1)
        attrs[key.strip()] = raw.strip().strip('"')
    return attrs


def safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch not in '/\\:*?"<>|' else "_" for ch in value).strip()
    return cleaned or "upload.psd"


def safe_join(root: Path, rel: Path) -> Path | None:
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    return target


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def render_home(error: str | None = None) -> str:
    error_block = ""
    if error:
        error_block = f"""
        <div class="mt-6 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
          <div class="font-semibold">转换失败</div>
          <pre class="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-red-100/80">{html.escape(error)}</pre>
        </div>
        """

    return page_shell(
        f"""
        <section class="mx-auto grid max-w-6xl gap-8 px-6 py-12 lg:grid-cols-[1.05fr_.95fr] lg:py-20">
          <div class="flex flex-col justify-center">
            <div class="mb-6 inline-flex w-fit rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-2 text-sm text-emerald-100">
              Local Photoshop Engine · No AI Required
            </div>
            <h1 class="max-w-3xl text-5xl font-semibold tracking-tight text-white md:text-6xl">
              PSD 自动转网页原型
            </h1>
            <p class="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              面向会务、活动页和医学会议 H5 的本地转换工具。运行在装有 Photoshop 的 Mac 上，上传 PSD 后自动生成预览页、结构化 JSON 和转换报告。
            </p>
            <div class="mt-8 grid gap-3 text-sm text-slate-300 sm:grid-cols-3">
              <div class="rounded-2xl border border-white/10 bg-white/[.04] p-4">Photoshop 高保真 flatten</div>
              <div class="rounded-2xl border border-white/10 bg-white/[.04] p-4">可编辑文字层提取</div>
              <div class="rounded-2xl border border-white/10 bg-white/[.04] p-4">本地处理，不上传云端</div>
            </div>
          </div>

          <div class="rounded-[2rem] border border-white/10 bg-white/[.06] p-6 shadow-2xl shadow-emerald-950/20 backdrop-blur">
            <div class="mb-6">
              <h2 class="text-2xl font-semibold text-white">开始转换</h2>
              <p class="mt-2 text-sm text-slate-400">请选择 PSD 文件和转换模式。转换时 Photoshop 会在本机后台执行。</p>
            </div>
            <form action="/convert" method="post" enctype="multipart/form-data" class="space-y-5">
              <label class="block rounded-2xl border border-dashed border-white/20 bg-slate-950/40 p-6 transition hover:border-emerald-300/50">
                <span class="block text-sm font-medium text-slate-200">PSD 文件</span>
                <input class="mt-4 block w-full cursor-pointer rounded-xl border border-white/10 bg-slate-950 p-3 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-400 file:px-4 file:py-2 file:font-medium file:text-slate-950" type="file" name="psd" accept=".psd" required />
              </label>
              <div>
                <label class="text-sm font-medium text-slate-200">转换模式</label>
                <select name="mode" class="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 p-3 text-slate-100 outline-none ring-emerald-300/30 focus:ring-4">
                  <option value="editable">可编辑模式</option>
                  <option value="fidelity">高保真模式</option>
                  <option value="assets">资产导出模式</option>
                </select>
              </div>
              <button class="w-full rounded-xl bg-emerald-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-emerald-300" type="submit">
                上传并转换
              </button>
            </form>
            {error_block}
          </div>
        </section>
        """
    )


def render_result(result: dict) -> str:
    job_id = result["job_id"]
    preview_url = f"/preview/{job_id}/index.html"
    download_url = f"/download/{job_id}"
    report = html.escape(result.get("report") or "")
    return page_shell(
        f"""
        <section class="mx-auto max-w-6xl px-6 py-12">
          <div class="rounded-[2rem] border border-white/10 bg-white/[.06] p-8 shadow-2xl shadow-emerald-950/20">
            <div class="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div class="text-sm text-emerald-200">转换完成</div>
                <h1 class="mt-2 text-3xl font-semibold text-white">{html.escape(result['filename'])}</h1>
                <p class="mt-2 text-slate-400">模式：{html.escape(result['mode'])} · 任务 ID：{job_id}</p>
              </div>
              <div class="flex flex-wrap gap-3">
                <a class="rounded-xl bg-emerald-400 px-5 py-3 font-semibold text-slate-950 hover:bg-emerald-300" href="{preview_url}" target="_blank" rel="noopener noreferrer">打开预览</a>
                <a class="rounded-xl border border-white/15 px-5 py-3 font-semibold text-white hover:bg-white/10" href="{download_url}">下载结果</a>
                <a class="rounded-xl border border-white/15 px-5 py-3 font-semibold text-white hover:bg-white/10" href="/">继续转换</a>
              </div>
            </div>
            <iframe class="mt-8 h-[720px] w-full rounded-2xl border border-white/10 bg-white" src="{preview_url}"></iframe>
            <div class="mt-8 rounded-2xl border border-white/10 bg-slate-950/70 p-5">
              <h2 class="text-lg font-semibold text-white">转换报告</h2>
              <pre class="mt-4 max-h-96 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">{report}</pre>
            </div>
          </div>
        </section>
        """
    )


def page_shell(content: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PSD Web Converter</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-[#080b12] text-slate-100">
  <div class="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_10%,rgba(16,185,129,.22),transparent_32%),radial-gradient(circle_at_80%_0%,rgba(59,130,246,.16),transparent_28%)]"></div>
  <header class="border-b border-white/10">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
      <a href="/" class="text-lg font-semibold tracking-tight text-white">PSD Web Converter</a>
      <div class="text-sm text-slate-400">Mac + Photoshop 本地运行</div>
    </div>
  </header>
  {content}
</body>
</html>"""


if __name__ == "__main__":
    main()
