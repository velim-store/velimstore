#!/usr/bin/env python3
"""Etapa 1: cria copias WEBP locais sem alterar covers.json ou index.html.

Cada imagem e baixada do URL atualmente configurado, redimensionada sem
recortar e validada. As URLs externas seguem ativas ate a aprovacao.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "covers"
REPORT = ROOT / "relatorios" / "importacao-capas-locais.json"
MAX_SIDE = 1024
MAX_DOWNLOAD = 20 * 1024 * 1024
MAX_WORKERS = 8
Image.MAX_IMAGE_PIXELS = 50_000_000

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    latin = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return (re.sub(r"[^a-z0-9]+", "-", latin).strip("-") or "jogo")[:85].rstrip("-")

def safe_output_name(name: str, used: set[str]) -> str:
    stem = slugify(name)
    candidate = stem + ".webp"
    if candidate in used:
        candidate = stem[:75] + "-" + hashlib.sha256(name.encode()).hexdigest()[:9] + ".webp"
    if candidate in used:
        raise RuntimeError("Colisao de nome de imagem: " + name)
    used.add(candidate)
    return candidate

def verify_webp(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        if image.format != "WEBP":
            raise ValueError("Arquivo nao esta em WebP")
        width, height = image.size
        if not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE):
            raise ValueError(f"Dimensao incorreta: {width}x{height}")
        return width, height

def fetch_image(url: str) -> bytes:
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Endereco nao HTTP(S)")
    domain = re.match(r"https?://([^/]+)", url, flags=re.IGNORECASE)
    if not domain:
        raise ValueError("Dominio invalido")
    referer = "https://" + domain.group(1) + "/"
    errors = []
    for attempt in range(3):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
        }
        if attempt > 0:
            headers["Referer"] = referer
        try:
            with requests.get(
                url, headers=headers, stream=True, timeout=(12, 32),
                allow_redirects=True
            ) as response:
                response.raise_for_status()
                result = io.BytesIO()
                count = 0
                for chunk in response.iter_content(64 * 1024):
                    count += len(chunk)
                    if count > MAX_DOWNLOAD:
                        raise ValueError("Imagem maior que o limite de 20 MB")
                    result.write(chunk)
                if count < 150:
                    raise ValueError("Resposta muito pequena para imagem")
                return result.getvalue()
        except (requests.RequestException, ValueError) as exc:
            errors.append(str(exc)[:180])
            if attempt < 2:
                time.sleep(1 + attempt * 2)
    raise RuntimeError(" | ".join(errors))

def convert_image(content: bytes, path: Path) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(content)) as image:
        image.load()
        original_size = list(image.size)
        if min(original_size) < 80:
            raise ValueError(f"Imagem pequena demais: {original_size}")
        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        if "A" in image.getbands() or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
        temp = path.with_suffix(".part.webp")
        try:
            image.save(temp, format="WEBP", quality=84, method=5)
            width, height = verify_webp(temp)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    return {
        "original_dimensions": original_size,
        "dimensions": [width, height],
        "download_bytes": len(content),
        "stored_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }

def process_one(item: dict) -> dict:
    name, url, local_path = item["name"], item["source_url"], item["local_path"]
    path = ROOT / local_path
    result = {"name": name, "source_url": url, "local_path": local_path}
    try:
        if path.exists():
            width, height = verify_webp(path)
            result.update(status="already_present", dimensions=[width, height],
                          stored_bytes=path.stat().st_size,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            return result
        raw = fetch_image(url)
        metadata = convert_image(raw, path)
        result.update(status="downloaded", **metadata)
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:420])
    return result

def main() -> None:
    covers = json.loads((ROOT / "covers.json").read_text(encoding="utf-8"))
    if len(covers) != 205:
        raise RuntimeError(f"Catalogo inesperado: {len(covers)} capas (esperado: 205)")
    names = [obj["name"] for obj in covers]
    if len(set(names)) != len(names):
        raise RuntimeError("Nomes duplicados no catalogo")
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tasks = []
    locally_configured = []
    used = set()
    for entry in covers:
        name, url = entry["name"], entry.get("imageUrl", "").strip()
        if url.startswith(("https://", "http://")):
            basename = safe_output_name(name, used)
            tasks.append({"name": name, "source_url": url,
                          "local_path": "assets/covers/" + basename})
        else:
            entry_status = {"name": name, "source_url": url, "local_path": url}
            try:
                local_file = (ROOT / url).resolve()
                if not local_file.is_file() or not local_file.is_relative_to(ROOT.resolve()):
                    raise ValueError("Arquivo local inexistente ou inseguro")
                with Image.open(local_file) as im:
                    im.verify()
                entry_status["status"] = "already_local"
            except Exception as exc:
                entry_status.update(status="failed", error=str(exc))
            locally_configured.append(entry_status)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(process_one, entry): entry for entry in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"[{len(results)}/{len(tasks)}] {result['status']}: {result['name']}", flush=True)
    results += locally_configured
    positions = {name: idx for idx, name in enumerate(names)}
    results.sort(key=lambda obj: positions[obj["name"]])

    ok_statuses = {"downloaded", "already_present", "already_local"}
    success = sum(obj["status"] in ok_statuses for obj in results)
    failed = [obj for obj in results if obj["status"] == "failed"]
    original_bytes = sum(obj.get("download_bytes", 0) for obj in results)
    compressed_bytes = sum(obj.get("stored_bytes", 0) for obj in results)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": "staging_only",
        "site_covers_switched": False,
        "max_side_px": MAX_SIDE,
        "output_format": "WebP",
        "webp_quality": 84,
        "total": len(results),
        "successful": success,
        "failed": len(failed),
        "external_downloads": len(tasks),
        "original_downloaded_bytes": original_bytes,
        "compressed_stored_bytes": compressed_bytes,
        "ready_to_migrate": success == len(covers),
        "images": results,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(
        f"FINAL: {success}/{len(covers)} verificados, {len(failed)} falhas. "
        "A pagina e covers.json NAO foram alterados.",
        flush=True,
    )
    if failed:
        print("FALHAS:", flush=True)
        for entry in failed:
            print(f" - {entry['name']}: {entry.get('error')}", flush=True)

if __name__ == "__main__":
    main()
