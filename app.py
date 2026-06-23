import os
import uuid
from flask import (
    Flask, request, jsonify,
    render_template, session, redirect, url_for
)
from dotenv import load_dotenv
from utils.file_handler import extract_text, allowed_file, is_image
from utils.ai_handler import summarize, chat, generate_flashcards
from utils.history_handler import (
    save_to_history, load_history,
    delete_from_history, get_entry
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'studyapp_secret_123')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  

text_store = {}



@app.errorhandler(413)
def file_too_large(e):
    return jsonify({'error': 'File too large! Maximum size is 50MB.'}), 413


@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('home'))


@app.route('/')
def home():
    """Home page — upload file + history."""
    return render_template('index.html')


@app.route('/summary')
def summary_page():
    """Summary page — shows exam-ready study notes."""
    entry_id = session.get('entry_id')
    if not entry_id:
        return redirect(url_for('home'))

    entry = get_entry(entry_id)
    if not entry:
        return redirect(url_for('home'))

    return render_template('summary.html', entry=entry)


@app.route('/chat_page')
def chat_page():
    """Chat page — ask questions about the document."""
    entry_id = session.get('entry_id')
    if not entry_id:
        return redirect(url_for('home'))

    entry = get_entry(entry_id)
    if not entry:
        return redirect(url_for('home'))

    return render_template('chat.html', entry=entry)


@app.route('/flashcard_page')
def flashcard_page():
    """Flashcards page — study with flashcards."""
    entry_id = session.get('entry_id')
    if not entry_id:
        return redirect(url_for('home'))

    entry = get_entry(entry_id)
    if not entry:
        return redirect(url_for('home'))

    return render_template('flashcards.html', entry=entry)



@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle file upload:
    1. Save file to uploads/
    2. Extract text
    3. Generate summary
    4. Save to history
    5. Return success
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported!'}), 400

    try:

        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            file.filename
        )
        file.save(filepath)

        text = extract_text(filepath)
        img = is_image(filepath)

        text_id = str(uuid.uuid4())
        text_store[text_id] = {
            'text': text,
            'filepath': filepath,
            'is_image': img
        }
        session['text_id'] = text_id

        if img:
            notes = summarize(filepath=filepath)
        else:
            notes = summarize(text=text)

        entry = save_to_history(
            file.filename,
            filepath,
            notes,
            text=text
        )

        session['entry_id'] = entry['id']

        return jsonify({'success': True})


    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    """Answer a question about the document."""
    data = request.get_json()
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'error': 'Please type a question!'}), 400

    stored = get_stored_data()
    if not stored:
        return jsonify({'error': 'Please upload a file first!'}), 400

    try:
        if stored['is_image']:
            answer = chat(question, filepath=stored['filepath'])
        else:
            answer = chat(question, text=stored['text'])
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_cards', methods=['POST'])
def generate_cards():
    """Generate flashcards from the document."""
    stored = get_stored_data()
    if not stored:
        return jsonify({'error': 'Please upload a file first!'}), 400

    try:
        if stored['is_image']:
            cards = generate_flashcards(filepath=stored['filepath'])
        else:
            cards = generate_flashcards(text=stored['text'])
        return jsonify({'flashcards': cards})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
def get_history():
    """Return all history entries."""
    history = load_history()

    display = [
        {
            'id': e['id'],
            'filename': e['filename'],
            'timestamp': e['timestamp']
        }
        for e in history
    ]
    return jsonify({'history': display})


@app.route('/load_entry', methods=['POST'])
def load_entry():
    """
    Load a past entry into the session.
    Called when user clicks a history item.
    """
    data = request.get_json()
    entry_id = data.get('id')

    entry = get_entry(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404

    text = entry.get('text')
    filepath = entry['filepath']
    img = is_image(filepath)

    text_id = str(uuid.uuid4())
    text_store[text_id] = {
        'text': text,
        'filepath': filepath,
        'is_image': img
    }
    session['text_id'] = text_id
    session['entry_id'] = entry_id

    return jsonify({'success': True})


@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    """Delete a history entry."""
    data = request.get_json()
    entry_id = data.get('id')

    try:
        delete_from_history(entry_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_stored_data():
    """
    Get the current document data from memory.
    Falls back to history file if not in memory
    (e.g. after server restart).
    """
    text_id = session.get('text_id')
    stored = text_store.get(text_id)

    if not stored:
        entry_id = session.get('entry_id')
        if not entry_id:
            return None

        entry = get_entry(entry_id)
        if not entry:
            return None

        text = entry.get('text')
        filepath = entry['filepath']
        stored = {
            'text': text,
            'filepath': filepath,
            'is_image': is_image(filepath)
        }

    return stored



if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, use_reloader=False)