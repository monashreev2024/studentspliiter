import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

HISTORY_DIR = os.path.join("data", "history")
INDEX_PATH = os.path.join(HISTORY_DIR, "index.json")


def ensure_history_store() -> None:
    os.makedirs(HISTORY_DIR, exist_ok=True)
    if not os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_index() -> List[Dict]:
    ensure_history_store()

    # If file doesn't exist or is empty → reset it
    if not os.path.exists(INDEX_PATH) or os.path.getsize(INDEX_PATH) == 0:
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # If corrupted → reset safely
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []


def _save_index(items: List[Dict]) -> None:
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def safe_filename(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_\-]", "", text)
    return text[:60] if text else "EVENT"


def build_output_filename(event_name: str, dt: datetime) -> str:
    event = safe_filename(event_name)
    stamp = dt.strftime("%Y-%m-%d_%H-%M")
    return f"{event}_{stamp}.xlsx"


def save_run(
    event_name: str,
    dt: datetime,
    uploaded_filename: str,
    output_filename: str,
    output_bytes: bytes,
) -> Dict:
    """
    Saves the generated Excel file + logs metadata in index.json
    Returns the saved record.
    """
    ensure_history_store()

    # Ensure unique file name if same timestamp/event repeats
    base_name = output_filename.replace(".xlsx", "")
    final_name = output_filename
    counter = 2
    while os.path.exists(os.path.join(HISTORY_DIR, final_name)):
        final_name = f"{base_name}_{counter}.xlsx"
        counter += 1

    file_path = os.path.join(HISTORY_DIR, final_name)
    with open(file_path, "wb") as f:
        f.write(output_bytes)

    record = {
        "id": f"{int(dt.timestamp())}_{final_name}",
        "event_name": event_name,
        "generated_at": dt.isoformat(timespec="minutes"),
        "uploaded_filename": uploaded_filename,
        "output_filename": final_name,
        "file_path": file_path,
    }

    items = _load_index()
    items.insert(0, record)  # newest first
    _save_index(items)

    return record


def list_history(limit: int = 30) -> List[Dict]:
    items = _load_index()
    return items[:limit]


def read_history_file(file_path: str) -> Optional[bytes]:
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception:
        return None


def delete_history_item(item_id: str) -> None:
    items = _load_index()
    keep = []
    for it in items:
        if it.get("id") == item_id:
            # delete file
            fp = it.get("file_path")
            if fp and os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass
        else:
            keep.append(it)
    _save_index(keep)
