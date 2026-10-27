#!/usr/bin/env python3
"""Busca capas nas páginas individuais do NSWVault; valida antes de substituir."""
import io
import json
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COVERS = ROOT / "covers.json"
REPORT = ROOT / "relatorios" / "varredura-nswvault-2026-10-26.md"
PAGE_ROOT = "https://nswvault.com/nintendo-switch/roms/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VelimStoreCoverAudit/1.0)"}
BAD_WORDS = {"switch", "nintendo", "for", "and", "the", "nsp", "xci", "dlc", "plus", "game", "edition"}
BAD_IMAGE = ("screenshot", "screencap", "screenshots", "screen-shot", "banner", "site-logo", "placeholder", "avatar", "icon", "thumbnail")

def slug(text):
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")

class Scanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.page_title = ""
        self.in_title = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in ("og:image", "twitter:image", "og:image:url"):
                self.images.append(("meta", a.get("content", "")))
            elif key in ("og:title", "twitter:title"):
                self.page_title = a.get("content", "") or self.page_title
        elif tag == "img":
            for field in ("src", "data-src"):
                url = a.get(field, "")
                if url:
                    self.images.append(("img", url))
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
    def handle_data(self, data):
        if self.in_title: self.page_title += data

def candidates(name, parser):
    tokens = set(slug(name).split("-")) - BAD_WORDS
    found = []
    for source, url in parser.images:
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("https://"):
            continue
        parts = urlsplit(url)
        if parts.netloc.lower() != "nswvault.com" or "/wp-content/uploads/" not in parts.path:
            continue
        basename = slug(unquote(parts.path.rsplit("/", 1)[-1]).rsplit(".", 1)[0])
        if any(w in basename for w in BAD_IMAGE):
            continue
        words = set(basename.split("-")) - BAD_WORDS
        shared = len(words & tokens)
        if not shared or shared / max(1, len(tokens)) < .5:
            continue
        score = shared / max(1, len(tokens)) + (1.0 if source == "meta" else 0.0)
        if basename == slug(name): score += 2
        found.append((score, source, url))
    return sorted(set(found), reverse=True)

def physical_switch_case(content):
    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
        w,h=img.size
        if w < 200 or h < 300 or not 0.48 <= w/h <= 0.86:
            return False, f"proporção/dimensões {w}x{h}"
        # O topo/esquerda de uma caixa oficial do Switch 1 tem tarja vermelha.
        count=0; total=0
        for yy in range(int(h*.03), max(int(h*.18),1), max(int(h*.15)//17,1)):
            for xx in range(int(w*.03),max(int(w*.23),1), max(int(w*.2)//17,1)):
                r,g,b=img.getpixel((xx,yy))
                total+=1
                if r>120 and r>g*1.6 and r>b*1.5: count+=1
        if count < max(7,total*.04):
            return False,f"sem faixa vermelha de Switch 1 ({count}/{total})"
        return True,f"capa {w}x{h}; vermelho {count}/{total}"
    except Exception as exc:
        return False, f"imagem inválida: {exc}"

def scan(entry):
    name=entry["name"]
    # O caminho é derivado do título da página, nunca da URL da imagem.
    # As URLs de imagens vêm exclusivamente do HTML real da página consultada.
    page=PAGE_ROOT + slug(name) + ".html"
    session=requests.Session()
    try:
        r=session.get(page,headers=HEADERS,timeout=15)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type",""):
            return name,page,None, f"página HTTP {r.status_code}"
        parser=Scanner()
        parser.feed(r.text)
        target=slug(name)
        actual=slug(parser.page_title)
        target_words=set(target.split("-")) - BAD_WORDS
        if len(target_words & set(actual.split("-"))) < max(1,len(target_words)//2):
            return name,page,None,"título da página incompatível"
        possibilities=candidates(name,parser)
        if not possibilities:
            return name,page,None,"sem URL de imagem compatível no HTML"
        failures=[]
        for _,_,url in possibilities[:3]:
            try:
                im=session.get(url,headers=HEADERS,timeout=15)
                if im.status_code!=200:
                    failures.append(f"imagem HTTP {im.status_code}")
                    continue
                if len(im.content)>8*1024*1024:
                    failures.append("imagem acima de 8 MB")
                    continue
                ok,detail=physical_switch_case(im.content)
                if ok:
                    return name,page,url,detail
                failures.append(detail)
            except Exception as exc:
                failures.append(str(exc)[:90])
        return name,page,None, "; ".join(failures)
    except Exception as exc:
        return name,page,None,"acesso falhou: "+str(exc)[:120]

def main():
    data=json.loads(COVERS.read_text(encoding="utf8"))
    target=[x for x in data if x.get("quality") == "mockup-provisorio"]
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(scan,x) for x in target]
        for future in as_completed(futures):
            results.append(future.result())
    matches={name:(page,img,reason) for name,page,img,reason in results if img}
    for entry in data:
        if entry["name"] in matches:
            _,url,_=matches[entry["name"]]
            entry["imageUrl"]=url
            entry["quality"]="capa-nswvault-verificada"
    if matches:
        COVERS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    output=[
       "# Varredura de capas NSWVault — 26/10/2026",
       "",
       "Consulta as páginas individuais de jogos; extrai URLs reais do HTML (og:image ou img); verifica título, imagem vertical e faixa vermelha do Switch 1.",
       "",
       f"- Capas provisórias verificadas: **{len(target)}**",
       f"- Capas substituídas: **{len(matches)}**",
       f"- Capas ainda pendentes: **{len(target)-len(matches)}**",
       "",
       "| Jogo | Página consultada | Imagem | Resultado |",
       "|---|---|---|---|",
    ]
    for name,page,url,reason in sorted(results):
        output.append(f"| {name.replace('|','/')} | {page} | {url or '—'} | {reason.replace('|','/')} |")
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text("\n".join(output)+"\n",encoding="utf8")
    print(json.dumps({"scanned":len(target),"updated":len(matches),"unresolved":len(target)-len(matches),"files":["covers.json" if matches else None,str(REPORT.relative_to(ROOT))]},ensure_ascii=False))
if __name__=="__main__":main()
