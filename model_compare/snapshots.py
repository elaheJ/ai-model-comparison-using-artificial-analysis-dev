"""Read snapshots as data only; never evaluate uploaded Python or notebooks."""
import csv
import hashlib
import io
import json
import os
import socket
import ssl
import certifi
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .core import has_measurement

MAX_BYTES = 10 * 1024 * 1024
BUNDLED_SNAPSHOT = Path(__file__).parent / "data" / "aa_snapshot.json"
FIELD_MAP = {
    "quality": ("evaluations", "artificial_analysis_intelligence_index"),
    "input_price": ("pricing", "price_1m_input_tokens"),
    "output_price": ("pricing", "price_1m_output_tokens"),
    "ttft_s": ("performance", "median_time_to_first_token_seconds"),
    "first_answer_s": ("performance", "median_time_to_first_answer_token_seconds"),
    "end_to_end_s": ("performance", "median_end_to_end_response_time_seconds"),
    "output_tokens_s": ("performance", "median_output_tokens_per_second"),
}


def normalize_snapshot(raw):
    if isinstance(raw, list):
        raw = {"models": raw}
    if not isinstance(raw, dict):
        raise ValueError("Snapshot must be an object with models (or data), or a list of model records.")
    if raw.get("pagination", {}).get("has_more"):
        raise ValueError("This API response is only one page. Export a complete snapshot using the fetch command.")
    models = raw.get("models", raw.get("data"))
    if not isinstance(models, list) or not 1 <= len(models) <= 1000:
        raise ValueError("A snapshot must contain 1–1,000 model records.")
    clean, seen = [], set()
    for number, record in enumerate(models, 1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {number} must be an object.")
        slug = record.get("slug")
        if not isinstance(slug, str) or not slug.strip() or len(slug) > 200:
            raise ValueError(f"Record {number} needs a nonempty slug (at most 200 characters).")
        if slug in seen:
            raise ValueError(f"Duplicate model ID: {slug}")
        seen.add(slug)
        name = record.get("name", slug)
        if not isinstance(name, str) or not name.strip() or len(name) > 300:
            raise ValueError(f"Record {number} has an invalid name.")
        creator = record.get("model_creator", record.get("creator", "Unknown")) or "Unknown"
        if isinstance(creator, dict):
            creator = creator.get("name", "Unknown")
        if not isinstance(creator, str) or len(creator) > 300:
            raise ValueError(f"Record {number} has an invalid creator.")
        row = {"slug": slug, "name": name, "model_creator": {"name": creator},
               "evaluations": {}, "performance": {}, "pricing": {}}
        for field, (group, key) in FIELD_MAP.items():
            section = record.get(group) or {}
            if not isinstance(section, dict):
                raise ValueError(f"Record {number}: {group} must be an object or null.")
            value = section.get(key, record.get(field))
            if value is not None and not (has_measurement(value) and 0 <= value <= 10**15):
                raise ValueError(f"Record {number}: {field} must be a finite nonnegative number or null.")
            row[group][key] = value
        # Only recognized fields are retained. Arbitrary upload fields cannot enter traces/prompts.
        clean.append(row)
    snapshot = {"schema_version": 1, "source": raw.get("source") or "User upload; source unspecified",
                "retrieved_at": raw.get("retrieved_at") or "Not recorded",
                "intelligence_index_version": raw.get("intelligence_index_version", "Not recorded"),
                "is_demo": raw.get("is_demo") is True, "models": clean}
    for key in ("source", "retrieved_at", "intelligence_index_version"):
        value = snapshot[key]
        if not isinstance(value, (str, int, float)) or isinstance(value, bool) or len(str(value)) > 500:
            raise ValueError(f"Invalid snapshot metadata: {key}")
        if isinstance(value, (int, float)) and not has_measurement(value):
            raise ValueError(f"Invalid snapshot metadata: {key}")
    snapshot["snapshot_id"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return snapshot


def load_snapshot(data, filename="snapshot.json"):
    if isinstance(data, str):
        data = data.encode()
    if len(data) > MAX_BYTES:
        raise ValueError("Snapshot exceeds the 10 MB upload limit.")
    try:
        text = data.decode("utf-8-sig")
        if filename.lower().endswith(".csv"):
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames or "slug" not in reader.fieldnames:
                raise ValueError("CSV needs a slug column; see the included CSV template.")
            rows = []
            for row in reader:
                for field in FIELD_MAP:
                    value = row.get(field, "")
                    row[field] = None if value is None or value.strip().lower() in ("", "null", "none", "na", "n/a") else float(value)
                rows.append(row)
            raw = {"models": rows, "source": "User CSV upload; source unspecified"}
        else:
            raw = json.loads(text)
        return normalize_snapshot(raw)
    except (UnicodeError, json.JSONDecodeError, TypeError, AttributeError, OverflowError, RecursionError) as exc:
        raise ValueError("Could not read snapshot. Use the documented JSON or CSV format.") from exc


def demo_snapshot():
    return load_snapshot((Path(__file__).parent / "data" / "demo_snapshot.json").read_bytes())


def default_snapshot():
    """Configured file, local download, bundled teaching snapshot, then demo."""
    configured = os.getenv("AA_SNAPSHOT_PATH")
    path = Path(configured).expanduser() if configured else Path.cwd() / "snapshots" / "aa_latest.json"
    if configured or path.is_file():
        return load_snapshot(path.read_bytes(), path.name)
    if BUNDLED_SNAPSHOT.is_file():
        return load_snapshot(BUNDLED_SNAPSHOT.read_bytes(), BUNDLED_SNAPSHOT.name)
    return demo_snapshot()


def configured_api_key():
    return os.getenv("AA_API_KEY", "").strip() or os.getenv("ARTIFICIAL_ANALYSIS_API_KEY", "").strip()


def fetch_artificial_analysis(api_key):
    """Explicit download only; an uploaded snapshot never triggers a network call."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("Set AA_API_KEY (or ARTIFICIAL_ANALYSIS_API_KEY) before fetching.")
    if any(ord(character) < 32 or ord(character) == 127 for character in api_key.strip()):
        raise ValueError("The API key must be a single line without control characters.")
    # Some macOS Python installations have no default CA file. Add the maintained
    # CA bundle without removing system/custom trust or disabling TLS validation.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    records, version = [], None
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for page_number in range(1, 11):
        request = Request(f"https://artificialanalysis.ai/api/v2/language/models/free?page={page_number}",
                          headers={"x-api-key": api_key.strip(), "User-Agent": "ModelComparisonLab/1.0"})
        try:
            with urlopen(request, timeout=30, context=context) as response:
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("API page exceeds the size limit.")
            page = json.loads(data)
            current = page["intelligence_index_version"]
            if version is not None and current != version:
                raise ValueError("Index version changed between pages; retry the download.")
            version = current
            records.extend(page["data"])
            if not page["pagination"]["has_more"]:
                return normalize_snapshot({"source": "https://artificialanalysis.ai", "retrieved_at": retrieved_at,
                                           "intelligence_index_version": version, "models": records})
        except HTTPError as exc:
            raise RuntimeError(f"Artificial Analysis returned HTTP {exc.code}. Check access and quota.") from None
        except (URLError, TimeoutError) as exc:
            reason = exc.reason if isinstance(exc, URLError) else exc
            if isinstance(reason, ssl.SSLCertVerificationError):
                message = "Artificial Analysis TLS certificate verification failed. Update certifi; if your network uses a custom certificate authority, configure SSL_CERT_FILE."
            elif isinstance(reason, socket.gaierror):
                message = "Could not resolve artificialanalysis.ai. Check your internet connection, DNS, or VPN."
            elif isinstance(reason, TimeoutError):
                message = "Artificial Analysis timed out after 30 seconds. Retry when the connection is available."
            else:
                message = "Could not connect to Artificial Analysis. Check your network, proxy, or firewall and retry."
            raise RuntimeError(message) from None
        except (KeyError, TypeError, json.JSONDecodeError):
            raise RuntimeError("Unexpected API response; check the current Artificial Analysis schema.") from None
    raise RuntimeError("Unexpected pagination: stopped after 10 pages.")
