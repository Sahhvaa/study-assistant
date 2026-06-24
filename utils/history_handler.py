import json
import os
from datetime import datetime

HISTORY_FILE = 'data/history.json'


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        return []

def save_to_history(filename, filepath, summary, text=None):
    """
    Save a new upload to history.
    We save the extracted text so it works
    even after server restarts (important for deployment).
    """
    history = load_history()

    entry = {
        'id': len(history) + 1,
        'filename': filename,
        'filepath': filepath,
        'text': text,
        'summary': summary,
        'timestamp': datetime.now().strftime('%d %b %Y, %I:%M %p')

    }

    history.append(entry)

    os.makedirs('data', exist_ok=True)

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    return entry


def delete_from_history(entry_id):
    """Delete one entry from history by its ID."""
    history = load_history()

    history = [e for e in history if e['id'] != entry_id]

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_entry(entry_id):
    """Get one specific entry by ID."""
    history = load_history()
    return next(
        (e for e in history if e['id'] == entry_id),
        None
 
    )