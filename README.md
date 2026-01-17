# StudyVault // The Academic Operating System

**StudyVault** is a high-performance, gamified productivity platform designed to turn academic pressure into tactical progress. Built to function like a "Video Game HUD" for students, it combines advanced task management, OCR automation, and squad-based collaboration into a single cyberpunk-inspired interface.

> **Status:** Active Development  
> **Version:** 1.0 (Protocol Genesis)

---

## ⚡ Key Features

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
* **Smart Toggling:** AJAX-powered checkboxes allow for instant task completion without page reloads.

### 📡 **Squadron Command**
Collaborative tools for group study operations.
* **Tactical Squads:** Users can deploy (create) or join squads using unique secure access codes.
* **Encrypted Comms:** A built-in, squad-specific chat room.
* **Pulse System:** Uses efficient AJAX polling to simulate real-time messaging without heavy WebSocket infrastructure.
* **Roster Management:** View active squad members and leadership hierarchy.

### 🔐 **Secure Identity Protocol**
* **Google OAuth Uplink:** One-click secure sign-in/sign-up.
* **Smart Sessions:** Users remain authenticated for 24 hours for seamless access.
* **Conflict Resolution:** Intelligent handling of duplicate email accounts between manual and social logins.

---

## 🛠️ Technical Stack

This project leverages a robust stack designed for rapid development and high interactivity.

* **Backend Framework:** Python // Django 5.x
* **Database:** SQLite (Development)
* **Frontend UI:** HTML5, Tailwind CSS (Utility-first styling)
* **Interactivity:** Vanilla JavaScript (Fetch API & AJAX)
* **OCR Engine:** Tesseract-OCR, PDF2Image, PDFPlumber
* **Authentication:** Django AllAuth (Social Account Integration)

---

## ⚙️ Installation & Local Setup

Follow these steps to deploy the system on your local machine.

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