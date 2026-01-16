from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Note, Exam, Topic, Profile
from .forms import NoteForm, ExamForm
import os
import re
from datetime import datetime, timedelta
from collections import Counter
import json

# --- PDF & OCR LIBRARIES ---
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance

# ==========================================
# ⚠️ SYSTEM CONFIGURATION ⚠️
# ==========================================
# Preserving your specific D: drive path
POPPLER_PATH = r"D:\Release-25.12.0-0\poppler-25.12.0\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ==========================================

def signin(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'signin.html', {'form': form})

@login_required(login_url='signin')
def dashboard(request):
    # --- HANDLE FORMS ---
    if request.method == 'POST' and 'add_exam' in request.POST:
        exam_form = ExamForm(request.POST)
        if exam_form.is_valid():
            exam = exam_form.save(commit=False)
            exam.user = request.user
            exam.save()
            return redirect('dashboard')

    if request.method == 'POST' and 'add_topic' in request.POST:
        exam_id = request.POST.get('exam_id')
        topic_name = request.POST.get('topic_name')
        if exam_id and topic_name:
            exam = get_object_or_404(Exam, id=exam_id, user=request.user)
            Topic.objects.create(exam=exam, name=topic_name, is_cho=False)
            return redirect('dashboard')

    # --- TOGGLE LOGIC WITH TIMESTAMPING ---
    if request.method == 'POST' and 'toggle_topic' in request.POST:
        topic_id = request.POST.get('topic_id')
        topic = get_object_or_404(Topic, id=topic_id, exam__user=request.user)
        topic.is_completed = not topic.is_completed
        
        # Save timestamp for activity tracker
        if topic.is_completed:
            topic.completed_at = timezone.now()
        else:
            topic.completed_at = None
            
        topic.save()
        return redirect('dashboard')

    # --- DASHBOARD DATA ---
    upcoming_exams = Exam.objects.filter(user=request.user, date__gte=timezone.now()).order_by('date')
    main_exam = upcoming_exams.first() if upcoming_exams.exists() else None
    online_count = Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()

    # 1. RADAR CHART DATA (Only show progress for missions that have CHO content)
    cho_missions = Exam.objects.filter(user=request.user, topics__is_cho=True).distinct()
    radar_labels = []
    radar_data = []
    for mission in cho_missions:
        radar_labels.append(mission.subject[:15]) 
        radar_data.append(mission.progress())

    # 2. ACTIVITY GRID DATA (Neural Link - Last 30 Days)
    days_to_show = 30
    today = timezone.now().date()
    start_date = today - timedelta(days=days_to_show - 1) 
    
    # Get Counts
    note_counts = Counter(
        Note.objects.filter(user=request.user, uploaded_at__date__gte=start_date)
        .values_list('uploaded_at__date', flat=True)
    )
    topic_counts = Counter(
        Topic.objects.filter(exam__user=request.user, completed_at__date__gte=start_date, is_completed=True)
        .values_list('completed_at__date', flat=True)
    )
    
    total_activity = note_counts + topic_counts
    
    # Build Grid
    activity_grid = []
    max_activity = max(max(total_activity.values(), default=1), 5) 

    for i in range(days_to_show):
        loop_date = start_date + timedelta(days=i)
        count = total_activity.get(loop_date, 0)
        
        # Calculate Color Intensity (0-4)
        intensity = 0
        if count > 0:
            ratio = count / max_activity
            if ratio > 0.75: intensity = 4
            elif ratio > 0.50: intensity = 3
            elif ratio > 0.25: intensity = 2
            else: intensity = 1
            
        activity_grid.append({
            'date': loop_date.strftime("%b %d"),
            'count': count,
            'intensity': intensity
        })

    # DEBUG PRINT: Watch your terminal to see if this appears!
    print(f"DEBUG: Dashboard loaded. Exams found: {upcoming_exams.count()}")

    context = {
        'main_exam': main_exam,
        'upcoming_exams': upcoming_exams,
        'online_count': online_count,
        'exam_form': ExamForm(),
        'radar_labels': json.dumps(radar_labels),
        'radar_data': radar_data,
        'activity_grid': activity_grid,
    }
    return render(request, 'dashboard.html', context)

@login_required(login_url='signin')
def notes_hub(request):
    query = request.GET.get('q')
    
    if request.method == 'POST':
        form = NoteForm(request.POST, request.FILES)
        
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()

            filename = note.file.name.lower()
            title = note.title.upper()

            # ====================================================
            # 1. HIGH-RES DATESHEET EXTRACTION (OCR)
            # ====================================================
            if "DATESHEET" in title or "DATESHEET" in filename.upper():
                print("--- STARTING HIGH-RES DATESHEET SCAN ---")
                extracted_count = 0
                
                try:
                    # 1. Convert to Images (DPI 400)
                    images = convert_from_path(note.file.path, poppler_path=POPPLER_PATH, dpi=400)
                    print(f"Processing {len(images)} pages...")

                    for i, img in enumerate(images):
                        # 2. Upscale (2x) & Enhance
                        width, height = img.size
                        img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
                        
                        img = img.convert('L') # Grayscale
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(2.0) # High Contrast

                        # 3. Read Text
                        raw_text = pytesseract.image_to_string(img, config='--psm 6')
                        lines = raw_text.split('\n')

                        for line in lines:
                            line = line.strip()
                            if len(line) < 10: continue
                            
                            # Clean OCR Noise
                            clean_line = line.replace('|', ' ').replace('!', ' ').replace(']', '1').upper()
                            clean_line = clean_line.replace('O', '0').replace('L', '1').replace('I', '1')

                            # 4. Find Date (Fuzzy Match)
                            date_pattern = r'(\d{1,2})[-/\s.]([A-Z]{3}|\d{1,2})[-/\s.](\d{4})'
                            date_match = re.search(date_pattern, clean_line)
                            
                            if date_match:
                                date_str = date_match.group(0)
                                
                                # 5. Extract Semester (for label)
                                sem_label = "Unknown"
                                sem_match = re.search(r'(\d+)\s*SEM', clean_line)
                                if sem_match:
                                    sem_label = f"Sem {sem_match.group(1)}"

                                # 6. Extract Subject
                                temp = clean_line.replace(date_str, '')
                                temp = re.sub(r'\d+\s*SEM', '', temp)
                                temp = re.sub(r'\b[A-Z0-9]{5,10}\b', '', temp) # Remove Codes
                                temp = temp.replace('MORNING', '').replace('EVENING', '').replace('CSE', '').replace('BRANCH', '').replace('SESSION', '')
                                
                                subject_name = temp.strip()

                                if len(subject_name) > 3 and not subject_name.isdigit():
                                    try:
                                        # Parse Date safely
                                        d_str = date_str.replace('.', '-').replace('/', '-')
                                        try:
                                            exam_date = datetime.strptime(d_str, "%d-%b-%Y")
                                        except:
                                            try:
                                                exam_date = datetime.strptime(d_str, "%d-%B-%Y")
                                            except:
                                                continue # Skip invalid dates

                                        final_date = timezone.make_aware(datetime(exam_date.year, exam_date.month, exam_date.day, 9, 0))
                                        
                                        # Deduplication check
                                        if not Exam.objects.filter(user=request.user, subject=subject_name.title(), date=final_date).exists():
                                            Exam.objects.create(
                                                user=request.user,
                                                subject=subject_name.title(),
                                                date=final_date,
                                                is_datesheet_entry=True,
                                                details=f"{sem_label} [Extracted]"
                                            )
                                            extracted_count += 1
                                            print(f"-> Saved: {subject_name}")
                                    except Exception as e:
                                        print(f"-> Date Skip: {e}")

                except Exception as e:
                    print(f"CRITICAL ERROR: {e}")
                    messages.error(request, f"Error: {e}")

                if extracted_count > 0:
                    messages.success(request, f"⚡ SUCCESS: {extracted_count} exams imported.")
                else:
                    messages.warning(request, "Scanned file but found no readable dates.")

            # ====================================================
            # 2. SYLLABUS EXTRACTION (CHO FILES)
            # ====================================================
            elif title.startswith('CHO') and filename.endswith('.pdf'):
                target_exam = Exam.objects.filter(user=request.user, date__gte=timezone.now()).order_by('date').first()
                if not target_exam:
                    target_exam = Exam.objects.create(user=request.user, subject="General Backlog", date=timezone.now() + timezone.timedelta(days=30))
                    messages.info(request, "Created 'General Backlog' for this protocol.")
                
                try:
                    extracted_count = 0
                    with pdfplumber.open(note.file.path) as pdf:
                        for page in pdf.pages:
                            tables = page.extract_tables()
                            for table in tables:
                                for row in table:
                                    if not row or len(row) < 2: continue
                                    lec_cell = str(row[0]).strip()
                                    if re.match(r'^[\d\s\-]+$', lec_cell):
                                        topic_cell = row[1] if row[1] else max(row, key=lambda x: len(str(x)))
                                        topic_text = str(topic_cell).replace('\n', ' ').strip()
                                        if len(topic_text) > 3:
                                            final_name = f"[Lec {lec_cell}] {topic_text}"
                                            Topic.objects.get_or_create(
                                                exam=target_exam, 
                                                name=final_name, 
                                                source_note=note, 
                                                defaults={'is_cho': True}
                                            )
                                            extracted_count += 1
                    
                    if extracted_count > 0:
                        messages.success(request, f"⚡ MAPPED {extracted_count} LECTURE MODULES.")

                except Exception as e:
                    print(f"Error: {e}")
                    messages.error(request, "File structure incompatible.")
            
            return redirect('notes_hub')
    
    notes = Note.objects.filter(user=request.user).order_by('-uploaded_at')
    if query:
        notes = notes.filter(title__icontains=query)

    context = {
        'notes': notes,
        'query': query if query else '',
        'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()
    }
    return render(request, 'notes_hub.html', context)

@login_required(login_url='signin')
def topics_hub(request):
    if request.method == 'POST' and 'toggle_topic' in request.POST:
        topic_id = request.POST.get('topic_id')
        topic = get_object_or_404(Topic, id=topic_id, exam__user=request.user)
        topic.is_completed = not topic.is_completed
        
        # Timestamping
        if topic.is_completed:
            topic.completed_at = timezone.now()
        else:
            topic.completed_at = None
            
        topic.save()
        return redirect('topics_hub')

    exams = Exam.objects.filter(
        user=request.user, 
        is_datesheet_entry=False,
        topics__is_cho=True 
    ).distinct().order_by('date')
    
    context = {'exams': exams, 'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()}
    return render(request, 'topics_hub.html', context)

@login_required(login_url='signin')
def datesheet_hub(request):
    search_query = request.GET.get('q', '')
    exams = Exam.objects.filter(user=request.user).order_by('date')
    if search_query: exams = exams.filter(subject__icontains=search_query)
    context = {'exams': exams, 'search_query': search_query, 'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()}
    return render(request, 'datesheet.html', context)

@login_required(login_url='signin')
@require_POST
def rename_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, exam__user=request.user)
    new_name = request.POST.get('new_name')
    if new_name:
        topic.name = new_name
        topic.save()
        messages.success(request, "Task parameters updated.")
    return redirect('topics_hub')

@login_required(login_url='signin')
@require_POST
def rename_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    new_subject = request.POST.get('new_subject')
    if new_subject:
        exam.subject = new_subject
        exam.save()
        messages.success(request, f"Mission protocol renamed to '{new_subject}'.")
    return redirect('topics_hub')

@login_required(login_url='signin')
def delete_mission(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    exam.delete()
    messages.success(request, "Mission aborted.")
    return redirect('topics_hub')

@login_required(login_url='signin')
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if note.file:
        try:
            if os.path.isfile(note.file.path):
                os.remove(note.file.path)
        except Exception:
            pass
    note.delete()
    messages.success(request, "Node decommissioned.")
    return redirect('notes_hub')

@login_required(login_url='signin')
@require_POST
def rename_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    new_title = request.POST.get('new_title')
    if new_title:
        note.title = new_title
        note.save()
        messages.success(request, "Node re-indexed.")
    return redirect('notes_hub')

@login_required(login_url='signin')
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    exam.delete()
    messages.success(request, "Exam removed from schedule.")
    return redirect('datesheet_hub')

@login_required(login_url='signin')
def clear_datesheet(request):
    if request.method == 'POST':
        count, _ = Exam.objects.filter(user=request.user).delete()
        messages.success(request, f"Master Schedule cleared. {count} items removed.")
    return redirect('datesheet_hub')

def home(request):
    return render(request, 'index.html')