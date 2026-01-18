import os
import pickle
import time
import numpy as np
import faiss
import google.generativeai as genai
from django.conf import settings
from .models import Note
import pdfplumber

# --- OCR IMPORTS ---
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance

# ⚠️ CONFIGURATION (Ensure these match your actual installation paths)
POPPLER_PATH = r"C:\Users\hs264\Downloads\Release-24.02.0-0\poppler-24.02.0\Library\bin" 
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 1. SETUP: Create a folder to store the "brain memory"
INDEX_DIR = os.path.join(settings.MEDIA_ROOT, 'vectors')
if not os.path.exists(INDEX_DIR):
    os.makedirs(INDEX_DIR)

def get_user_index_path(user_id):
    return os.path.join(INDEX_DIR, f"user_{user_id}.index")

def get_user_chunks_path(user_id):
    return os.path.join(INDEX_DIR, f"user_{user_id}.pkl")

# 2. CONNECT: Wake up Gemini
def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        return None
    genai.configure(api_key=api_key)
    return genai

# 3. HELPER: OCR Function (Reads Images)
def extract_text_with_ocr(pdf_path):
    print("👁️ AI: Switching to Vision Mode (OCR)...")
    text = ""
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=150)
        for i, img in enumerate(images):
            img = img.convert('L')
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            page_text = pytesseract.image_to_string(img)
            text += page_text + "\n"
    except Exception as e:
        print(f"❌ OCR Failed: {e}")
    return text

# 4. HELPER: Safe Embedding with Retry
def safe_embed_batch(client, batch, title, retries=3):
    """Tries to embed. If blocked (429), waits and retries."""
    for attempt in range(retries):
        try:
            # Using the modern embedding model
            result = client.embed_content(
                model="models/text-embedding-004",
                content=batch,
                task_type="retrieval_document",
                title=title
            )
            return np.array(result['embedding'], dtype='float32')
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = 60 # Wait 1 minute if blocked
                print(f"   ⚠️ Quota Hit! Waiting {wait_time}s before retry ({attempt+1}/{retries})...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Error: {e}")
                return None
    return None

# 5. LEARN: Read a PDF and memorize it
def add_note_to_vault(note):
    print(f"🧠 AI: Reading note '{note.title}'...")
    genai_client = get_gemini_model()
    if not genai_client or not note.file:
        return False

    # A. Extract Text
    text = ""
    try:
        with pdfplumber.open(note.file.path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: text += t + "\n"
    except: pass

    # B. Fallback to OCR
    if len(text) < 100:
        text = extract_text_with_ocr(note.file.path)

    if len(text) < 50:
        print("❌ Failed: File is unreadable.")
        return False

    # C. Chunk Text
    chunk_size = 1000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    # D. Embed with Smart Batching
    all_embeddings = []
    batch_size = 5
    
    print(f"   - Processing {len(chunks)} chunks in batches of {batch_size}...")

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        batch_embeddings = safe_embed_batch(genai_client, batch, note.title)
        
        if batch_embeddings is None:
            print("❌ Failed to embed batch after retries. Aborting.")
            return False
            
        if len(all_embeddings) == 0:
            all_embeddings = batch_embeddings
        else:
            all_embeddings = np.vstack([all_embeddings, batch_embeddings])
        
        time.sleep(2)

    # E. Save to FAISS
    index_path = get_user_index_path(note.user.id)
    chunks_path = get_user_chunks_path(note.user.id)

    if os.path.exists(index_path) and os.path.exists(chunks_path):
        index = faiss.read_index(index_path)
        with open(chunks_path, 'rb') as f:
            stored_chunks = pickle.load(f)
    else:
        index = faiss.IndexFlatL2(768)
        stored_chunks = []

    index.add(all_embeddings)
    stored_chunks.extend(chunks)

    faiss.write_index(index, index_path)
    with open(chunks_path, 'wb') as f:
        pickle.dump(stored_chunks, f)

    print("✅ AI: Note memorized successfully.")
    return True

# 6. THINK: Answer a question
def ask_vault(user, question):
    genai_client = get_gemini_model()
    if not genai_client: return "System Error: AI Key missing."

    index_path = get_user_index_path(user.id)
    chunks_path = get_user_chunks_path(user.id)

    if not os.path.exists(index_path):
        return "Vault is empty. Upload a PDF first!"

    # Get embedding for the question
    q_embedding = safe_embed_batch(genai_client, question, "User Query")
    
    if q_embedding is None:
        return "System Overload: AI is taking a break. Try again in 1 minute."
        
    # Reshape for FAISS
    q_vector = q_embedding.reshape(1, -1)

    index = faiss.read_index(index_path)
    with open(chunks_path, 'rb') as f:
        stored_chunks = pickle.load(f)
    
    k = 5 
    distances, indices = index.search(q_vector, k)
    
    relevant_context = ""
    for idx in indices[0]:
        if idx < len(stored_chunks):
            relevant_context += stored_chunks[idx] + "\n\n"

    # --- UPGRADE: Use Gemini 2.5 Flash ---
    prompt = f"""
    You are StudyVault AI. Answer using ONLY the context below.
    CONTEXT:
    {relevant_context}
    QUESTION:
    {question}
    """
    
    # 2.5 Flash is the stable model for 2026
    model = genai_client.GenerativeModel('gemini-2.5-flash')
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"I'm having trouble thinking right now. Error: {str(e)}"