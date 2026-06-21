"""Download public knowledge sources into ``library/`` for ingestion.

This is the *fetch* step that feeds ``scripts/ingest_knowledge.py``: it reads a
curated manifest (``scripts/sources.yaml``) and downloads each listed source
into the matching ``library/<family>/`` folder, where the ingester then cleans
and chunks it into the committed ``knowledge/`` notes.

Legitimacy by construction
---------------------------
- It only fetches URLs **you** put in the manifest (an allow-list), so it never
  trawls for or pirates copyrighted books. Per ``docs/sme_knowledge_base.md``
  §4.8, books are distilled into your own notes — not bulk-downloaded.
- Only ``http``/``https`` URLs are allowed.
- It honors ``robots.txt`` (toggle in the manifest), rate-limits between
  requests, sends a descriptive User-Agent, caps file size, and skips files
  already on disk (unless ``--overwrite``).

Modes
-----
- ``file`` (default): download the URL directly.
- ``page``: fetch an HTML page and download the same-domain *document* links on
  it (``.pdf``/``.docx``/``.xls``/``.xlsx``/``.csv`` by default, configurable via
  ``settings.document_exts``; capped by ``settings.max_page_links``) — handy for
  "all bulletins on this index page" style official sources. It reads only that
  one page (no crawling) and only same-domain links.

Usage
-----
    python scripts/download_sources.py --dry-run          # show the plan
    python scripts/download_sources.py                    # download enabled entries
    python scripts/download_sources.py --family B         # only family B
    python scripts/download_sources.py --only "RBI"       # name substring filter

Requires ``httpx`` (already a project dep) and ``PyYAML``.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MANIFEST = _REPO_ROOT / "scripts" / "sources.yaml"
_DEFAULT_OUT = _REPO_ROOT / "library"

# Family tag -> library/ sub-folder (mirrors ingest_knowledge._FAMILY_PREFIX so
# downloads land where the ingester infers the same family back).
_FAMILY_DIR = {"A": "family_a", "B": "family_b", "C": "family_c", "RISK": "risk", "all": ""}

# Map a response content-type to a file extension when the URL has none.
_CONTENT_TYPE_EXT = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
_KNOWN_EXTS = {".pdf", ".html", ".htm", ".docx", ".doc", ".xls", ".xlsx", ".csv", ".txt", ".md"}
_ALLOWED_SCHEMES = {"http", "https"}

# Document types mode:page collects by default. PDFs/DOCX feed the knowledge
# ingester; XLS/CSV are pulled as raw data (the ingester won't chunk those, but
# they're useful as analysis inputs in library/).
_DEFAULT_DOC_EXTS = (".pdf", ".docx", ".doc", ".xls", ".xlsx", ".csv")


def _href_regex(exts: tuple[str, ...]):
    """Compile an href matcher for any of the given file extensions."""
    alternation = "|".join(re.escape(e.lstrip(".")) for e in exts)
    return re.compile(
        rf"""href\s*=\s*["']([^"']+?\.(?:{alternation})(?:\?[^"']*)?)["']""",
        re.IGNORECASE,
    )


class DownloadError(RuntimeError):
    """Raised when a source cannot be fetched or is rejected by policy."""


@dataclass
class Settings:
    user_agent: str = "ats-knowledge-downloader/1.0 (+local research; respects robots.txt)"
    rate_limit_s: float = 2.0
    timeout_s: float = 30.0
    respect_robots: bool = True
    max_file_mb: int = 100
    max_page_links: int = 25
    document_exts: tuple[str, ...] = _DEFAULT_DOC_EXTS


@dataclass
class Source:
    name: str
    family: str = "all"
    url: str = ""
    reliability: int | None = None
    mode: str = "file"
    enabled: bool = True


@dataclass
class Manifest:
    settings: Settings = field(default_factory=Settings)
    sources: list[Source] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Pure helpers (no network — unit tested)                                      #
# --------------------------------------------------------------------------- #
def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "source"


def is_allowed_url(url: str) -> bool:
    """Only absolute http(s) URLs are permitted (blocks file://, ftp://, ...)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)


def normalize_family(value: str | None) -> str:
    fam = (value or "all").strip()
    upper = fam.upper()
    if upper in {"A", "B", "C", "RISK"}:
        return upper
    return "all"


def family_dir(family: str) -> str:
    return _FAMILY_DIR.get(normalize_family(family), "")


def guess_extension(url: str, content_type: str | None) -> str:
    """Pick a sensible file extension from the URL, falling back to content-type."""
    path_ext = Path(urlparse(url).path).suffix.lower()
    if path_ext in _KNOWN_EXTS:
        return path_ext
    if content_type:
        base = content_type.split(";", 1)[0].strip().lower()
        if base in _CONTENT_TYPE_EXT:
            return _CONTENT_TYPE_EXT[base]
    return ".pdf" if path_ext == "" else path_ext


def target_path(out_root: Path, family: str, name: str, ext: str) -> Path:
    sub = family_dir(family)
    folder = out_root / sub if sub else out_root
    return folder / f"{slugify(name)}{ext}"


def extract_document_links(
    html: str,
    base_url: str,
    *,
    exts: tuple[str, ...] = _DEFAULT_DOC_EXTS,
    same_domain: bool = True,
) -> list[str]:
    """Find absolute document links (by extension) in a page.

    Restricted to the page's own host by default. Returns de-duplicated,
    http(s)-only absolute URLs in document order.
    """
    base_host = urlparse(base_url).netloc
    pattern = _href_regex(exts)
    out: list[str] = []
    seen: set[str] = set()
    for href in pattern.findall(html):
        absolute = urljoin(base_url, href)
        if not is_allowed_url(absolute):
            continue
        if same_domain and urlparse(absolute).netloc != base_host:
            continue
        if absolute not in seen:
            seen.add(absolute)
            out.append(absolute)
    return out


def parse_manifest(data: dict) -> Manifest:
    """Build a :class:`Manifest` from already-parsed YAML (dict)."""
    raw_settings = data.get("settings") or {}
    raw_exts = raw_settings.get("document_exts")
    if raw_exts:
        document_exts = tuple(
            ("." + str(e).lstrip(".")).lower() for e in raw_exts if str(e).strip()
        )
    else:
        document_exts = _DEFAULT_DOC_EXTS
    settings = Settings(
        user_agent=str(raw_settings.get("user_agent", Settings.user_agent)),
        rate_limit_s=float(raw_settings.get("rate_limit_s", Settings.rate_limit_s)),
        timeout_s=float(raw_settings.get("timeout_s", Settings.timeout_s)),
        respect_robots=bool(raw_settings.get("respect_robots", True)),
        max_file_mb=int(raw_settings.get("max_file_mb", Settings.max_file_mb)),
        max_page_links=int(raw_settings.get("max_page_links", Settings.max_page_links)),
        document_exts=document_exts,
    )
    sources: list[Source] = []
    for item in data.get("sources") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        reliability = item.get("reliability")
        sources.append(
            Source(
                name=str(item["name"]),
                family=normalize_family(item.get("family")),
                url=str(item.get("url") or "").strip(),
                reliability=int(reliability) if reliability is not None else None,
                mode=str(item.get("mode") or "file").strip().lower(),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return Manifest(settings=settings, sources=sources)


def load_manifest(path: Path) -> Manifest:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise DownloadError(f"manifest must be a YAML mapping: {path}")
    return parse_manifest(data)


# --------------------------------------------------------------------------- #
# Network                                                                      #
# --------------------------------------------------------------------------- #
class _RobotsCache:
    """Per-host robots.txt cache; fails open (allow) when robots is unreachable."""

    def __init__(self, user_agent: str, timeout_s: float) -> None:
        self._ua = user_agent
        self._timeout = timeout_s
        self._cache: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        import httpx

        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._cache:
            robots_url = f"{host}/robots.txt"
            rp: RobotFileParser | None = RobotFileParser()
            try:
                resp = httpx.get(
                    robots_url,
                    headers={"User-Agent": self._ua},
                    timeout=self._timeout,
                    follow_redirects=True,
                )
                if resp.status_code >= 400:
                    rp = None  # no robots policy published -> allow
                else:
                    rp.parse(resp.text.splitlines())
            except Exception:  # noqa: BLE001 - robots unreachable -> allow
                rp = None
            self._cache[host] = rp
        rp = self._cache[host]
        return True if rp is None else rp.can_fetch(self._ua, url)


def _download_one(url: str, dest: Path, settings: Settings, *, dry_run: bool) -> str:
    """Stream a single URL to ``dest`` with a size cap. Returns a status note."""
    import httpx

    if dry_run:
        return f"dry-run -> {dest}"
    max_bytes = settings.max_file_mb * 1024 * 1024
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    written = 0
    headers = {"User-Agent": settings.user_agent}
    with httpx.stream("GET", url, headers=headers, timeout=settings.timeout_s,
                      follow_redirects=True) as resp:
        resp.raise_for_status()
        # Re-validate the final URL after any redirects (defense in depth).
        if not is_allowed_url(str(resp.url)):
            raise DownloadError(f"redirected to a disallowed URL: {resp.url}")
        with tmp.open("wb") as fh:
            for chunk in resp.iter_bytes():
                written += len(chunk)
                if written > max_bytes:
                    fh.close()
                    tmp.unlink(missing_ok=True)
                    raise DownloadError(f"exceeds max_file_mb={settings.max_file_mb}")
                fh.write(chunk)
    tmp.replace(dest)
    return f"{written // 1024} KB -> {dest}"


def _resolve_targets(
    source: Source, settings: Settings, robots: _RobotsCache, out_root: Path
) -> list[tuple[str, Path]]:
    """Expand a source into concrete (url, dest) download jobs."""
    import httpx

    if source.mode == "page":
        if settings.respect_robots and not robots.allowed(source.url):
            raise DownloadError("blocked by robots.txt")
        resp = httpx.get(
            source.url,
            headers={"User-Agent": settings.user_agent},
            timeout=settings.timeout_s,
            follow_redirects=True,
        )
        resp.raise_for_status()
        links = extract_document_links(
            resp.text, str(resp.url), exts=settings.document_exts
        )[: settings.max_page_links]
        jobs: list[tuple[str, Path]] = []
        for link in links:
            stem = Path(urlparse(link).path).stem or "doc"
            ext = guess_extension(link, None)
            dest = target_path(out_root, source.family, f"{source.name} {stem}", ext)
            jobs.append((link, dest))
        if not jobs:
            raise DownloadError("no document links found on page")
        return jobs

    # mode: file (default)
    ext = guess_extension(source.url, None)
    return [(source.url, target_path(out_root, source.family, source.name, ext))]


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #
def run(
    manifest: Manifest,
    *,
    out_root: Path,
    family_filter: str | None,
    only: str | None,
    dry_run: bool,
    overwrite: bool,
) -> tuple[int, int, int]:
    """Returns (downloaded, skipped, failed)."""
    settings = manifest.settings
    robots = _RobotsCache(settings.user_agent, settings.timeout_s)
    downloaded = skipped = failed = 0
    last_request = 0.0

    for source in manifest.sources:
        label = source.name
        if family_filter and normalize_family(source.family) != normalize_family(family_filter):
            continue
        if only and only.lower() not in source.name.lower():
            continue
        if not source.enabled:
            print(f"  SKIP {label}: disabled (TODO entry)")
            skipped += 1
            continue
        if not source.url:
            print(f"  SKIP {label}: no url set")
            skipped += 1
            continue
        if not is_allowed_url(source.url):
            print(f"  SKIP {label}: not an http(s) URL")
            skipped += 1
            continue

        try:
            jobs = _resolve_targets(source, settings, robots, out_root)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {label}: {exc}")
            failed += 1
            continue

        for url, dest in jobs:
            if dest.exists() and not overwrite and not dry_run:
                print(f"  SKIP {label}: exists ({dest.name}; use --overwrite)")
                skipped += 1
                continue
            if settings.respect_robots and not dry_run and not robots.allowed(url):
                print(f"  SKIP {label}: blocked by robots.txt ({url})")
                skipped += 1
                continue
            # Polite rate limit between actual network hits.
            if not dry_run:
                wait = settings.rate_limit_s - (time.monotonic() - last_request)
                if wait > 0:
                    time.sleep(wait)
                last_request = time.monotonic()
            try:
                note = _download_one(url, dest, settings, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001
                print(f"  FAIL {label}: {exc}")
                failed += 1
                continue
            downloaded += 1
            print(f"  OK   {label}  ({note})")

    return downloaded, skipped, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download public knowledge sources into library/.")
    parser.add_argument("--manifest", default=str(_DEFAULT_MANIFEST),
                        help="path to sources.yaml (default: scripts/sources.yaml)")
    parser.add_argument("--out", default=str(_DEFAULT_OUT),
                        help="output root (default: library/)")
    parser.add_argument("--family", choices=["A", "B", "C", "RISK", "all"], default=None,
                        help="only download this family")
    parser.add_argument("--only", default=None, help="name substring filter")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, fetch nothing")
    parser.add_argument("--overwrite", action="store_true", help="re-download existing files")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    try:
        manifest = load_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not read manifest: {exc}", file=sys.stderr)
        return 2

    out_root = Path(args.out)
    enabled = sum(1 for s in manifest.sources if s.enabled and s.url)
    print(f"manifest: {manifest_path}  ({len(manifest.sources)} sources, {enabled} ready)"
          f"{' [dry-run]' if args.dry_run else ''}\n")

    downloaded, skipped, failed = run(
        manifest,
        out_root=out_root,
        family_filter=args.family,
        only=args.only,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )

    print(f"\ndone: {downloaded} downloaded, {skipped} skipped, {failed} failed.")
    if downloaded and not args.dry_run:
        print("Next: python scripts/ingest_knowledge.py   # clean library/ -> knowledge/")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
