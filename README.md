# StudyVault // The Academic Operating System

**StudyVault** is a high-performance, gamified productivity platform designed to turn academic pressure into tactical progress. Built to function like a "Video Game HUD" for students, it combines advanced task management, OCR automation, and **AI-powered RAG intelligence** into a single cyberpunk-inspired interface.

> **Status:** Active Development  
> **Version:** 2.5 (Neural Update)

---

## ⚡ Key Features

### 🧠 **The Vault (Neural RAG Engine)**
*New in v2.0* — A fully integrated Retrieval-Augmented Generation system.
* **Talk to Your Notes:** Upload PDF textbooks or handwritten notes. The system embeds them into a vector database (FAISS), allowing you to chat with your documents.
* **On-Demand Flashcards:** Command the AI to *"Make flashcards for Chapter 4,"* and it generates interactive, flip-able cards instantly using a strict generation protocol.
* **Tactical Quizzes:** The AI creates interactive Multiple Choice Questions (MCQs) to test your knowledge on specific topics.
* **Smart Model Fallback:** Automatically rotates between Google Gemini models (1.5 Flash, 2.0 Flash) to ensure uptime even when API rate limits are hit.
* **Draggable Interface:** A resizing, floating chat widget that behaves like a "browser-in-browser" for seamless multitasking.

### 🎮 **The Neural Dashboard**
A central command center that gamifies the study experience.
* **XP & Leveling Engine:** Completing tasks awards XP, leveling the user from "Novice" to "Operative."
* **Activity Heatmap:** Visualizes study consistency over the last 30 days (similar to GitHub contributions).
* **Dynamic Skill Trees:** Automatically tracks progress across different subjects based on completed modules.
* **Live Operative Status:** Real-time counter showing other active users on the platform.

### 🤖 **Mission Control (OCR Automation)**
Why type to-do lists when you can scan them?
* **Syllabus Injection:** Upload a PDF syllabus, and the system uses **OCR (Tesseract & Poppler)** to read the text.
* **Auto-Parsing:** Automatically detects lecture numbers and topics, converting them into trackable database objects.
* **Datesheet Scanner:** Upload an exam schedule, and the system extracts dates and subjects to auto-populate the calendar.

### 📡 **Squadron Command**
Collaborative tools for group study operations.
* **Tactical Squads:** Users can deploy (create) or join squads using unique secure access codes.
* **Encrypted Comms:** A built-in, squad-specific chat room.
* **Pulse System:** Uses efficient AJAX polling to simulate real-time messaging without heavy WebSocket infrastructure.

---

## 🛠️ Technical Stack

This project leverages a hybrid stack combining traditional web frameworks with modern AI pipelines.

* **Backend Framework:** Python // Django 5.x
* **Artificial Intelligence:** Google Gemini API (1.5 & 2.5 Flash)
* **Vector Database:** FAISS (Facebook AI Similarity Search) & NumPy
* **Database:** SQLite (Development)
* **Frontend UI:** HTML5, Tailwind CSS, Marked.js (Markdown), Highlight.js
* **OCR Engine:** Tesseract-OCR, Poppler, PDFPlumber
* **Authentication:** Django AllAuth (Social Account Integration)

---

## ⚙️ Installation & Local Setup

### 1. Clone the Repository
Open your terminal and clone the project files to your local directory.

### 2. Environment Setup
Create a virtual environment to keep dependencies isolated.
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
