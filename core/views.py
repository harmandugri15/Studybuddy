from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count, Q
from .models import Note, Exam, Topic, Profile
from .forms import NoteForm, ExamForm
import os
import re
from datetime import datetime, timedelta
from collections import Counter
import json
from django.contrib.auth import logout

# --- PDF & OCR LIBRARIES ---
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance

# ⚠️ CONFIGURATION
POPPLER_PATH = r"D:\Release-25.12.0-0\poppler-25.12.0\Library\bin" 
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def signout(request):
    logout(request)
    return redirect('home')

def signin(request):
    
    if request.user.is_authenticated:
        return redirect('dashboard')
    
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

    # --- TOGGLE LOGIC ---
    if request.method == 'POST' and 'toggle_topic' in request.POST:
        topic_id = request.POST.get('topic_id')
        topic = get_object_or_404(Topic, id=topic_id, exam__user=request.user)
        topic.is_completed = not topic.is_completed
        if topic.is_completed:
            topic.completed_at = timezone.now()
        else:
            topic.completed_at = None
        topic.save()
        return redirect('dashboard')

    # =========================================
    # 1. FETCH ALL DATA
    # =========================================
    # All active exams (excluding Datesheet entries)
    all_active_exams = Exam.objects.filter(user=request.user, is_datesheet_entry=False)
    
    # 1a. PRIMARY OBJECTIVE LOGIC (Most Completed First)
    # We sort the exams by their progress() method in descending order
    # If no progress, it defaults to sorting by ID
    active_exams_list = list(all_active_exams)
    active_exams_list.sort(key=lambda x: x.progress(), reverse=True)
    
    main_exam = active_exams_list[0] if active_exams_list else None

    # =========================================
    # 2. SKILL TREE DATA (CHO ONLY)
    # =========================================
    # Filter: Only exams that have at least one Topic marked as is_cho=True
    cho_only_missions = Exam.objects.filter(
        user=request.user, 
        is_datesheet_entry=False, 
        topics__is_cho=True
    ).distinct()

    # Sort these by task count (size of syllabus) to find the biggest subjects
    top_cho_qs = cho_only_missions.annotate(task_count=Count('topics')).order_by('-task_count')[:5]
    
    skill_labels = []
    skill_values = [] 
    
    for m in top_cho_qs:
        skill_labels.append(m.subject)
        skill_values.append(m.progress())
    
    # Pad defaults if less than 5 CHO missions exist
    while len(skill_labels) < 5:
        skill_labels.append("LOCKED")
        skill_values.append(0)

    # =========================================
    # 3. STATS CALCULATIONS
    # =========================================
    total_missions = all_active_exams.count()
    # Skills count is now strictly CHO based
    total_skills = cho_only_missions.count()
    
    completed_tasks = Topic.objects.filter(exam__user=request.user, is_completed=True).count()
    current_xp = completed_tasks * 100
    user_level = int(current_xp / 500) + 1 

    total_progress = 0
    if total_missions > 0:
        for mission in all_active_exams:
            total_progress += mission.progress()
        global_completion = int(total_progress / total_missions)
    else:
        global_completion = 0

    # Streak Logic
    note_dates = list(Note.objects.filter(user=request.user).values_list('uploaded_at__date', flat=True))
    topic_dates = list(Topic.objects.filter(exam__user=request.user, is_completed=True).values_list('completed_at__date', flat=True))
    all_dates = sorted(list(set(note_dates + topic_dates)), reverse=True)
    streak = 0
    if all_dates:
        today = timezone.now().date()
        check_date = today
        if all_dates[0] == today:
            streak = 1
            check_date = today - timedelta(days=1)
        elif all_dates[0] == today - timedelta(days=1):
            streak = 0 
            check_date = today - timedelta(days=1)
        
        for date in all_dates:
            if date == check_date:
                streak += 1
                check_date -= timedelta(days=1)
            elif date > check_date: continue 
            else: break 

    # =========================================
    # 4. ACTIVITY STREAM
    # =========================================
    days_to_show = 30
    today = timezone.now().date()
    start_date = today - timedelta(days=days_to_show - 1) 
    note_counts = Counter(Note.objects.filter(user=request.user, uploaded_at__date__gte=start_date).values_list('uploaded_at__date', flat=True))
    topic_counts = Counter(Topic.objects.filter(exam__user=request.user, completed_at__date__gte=start_date, is_completed=True).values_list('completed_at__date', flat=True))
    total_activity = note_counts + topic_counts
    activity_grid = []
    max_activity = max(max(total_activity.values(), default=1), 4)

    for i in range(days_to_show):
        loop_date = start_date + timedelta(days=i)
        count = total_activity.get(loop_date, 0)
        if count == 0:
            height_pct = 10
            intensity = 0
        else:
            height_pct = min(100, max(20, (count / max_activity) * 100))
            intensity = 1 if count == 1 else (2 if count <= 3 else 3)
        activity_grid.append({'date': loop_date.strftime("%b %d"), 'count': count, 'height': height_pct, 'intensity': intensity})

    # Upcoming List (Standard Sort by Date)
    upcoming_exams = Exam.objects.filter(user=request.user, date__gte=timezone.now()).order_by('date')
    online_count = Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()

    context = {
        'main_exam': main_exam, # Now sorted by HIGHEST PROGRESS
        'upcoming_exams': upcoming_exams,
        'online_count': online_count,
        'exam_form': ExamForm(),
        'user_level': user_level,
        'total_missions': total_missions,
        'streak': streak,
        'total_skills': total_skills,
        'global_completion': global_completion,
        
        # Skill Tree Data (CHO Only)
        'skill_1': skill_labels[0],
        'skill_2': skill_labels[1],
        'skill_3': skill_labels[2],
        'skill_4': skill_labels[3],
        'skill_5': skill_labels[4],
        'skill_values': json.dumps(skill_values), 
        'skill_labels_list': json.dumps(skill_labels),
        
        'activity_grid': activity_grid,
    }
    return render(request, 'dashboard.html', context)

# ... (Keep remaining views unchanged) ...
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
                    images = convert_from_path(note.file.path, poppler_path=POPPLER_PATH, dpi=400)
                    print(f"Processing {len(images)} pages...")

                    for i, img in enumerate(images):
                        width, height = img.size
                        img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
                        img = img.convert('L') 
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(2.0) 

                        raw_text = pytesseract.image_to_string(img, config='--psm 6')
                        lines = raw_text.split('\n')

                        for line in lines:
                            line = line.strip()
                            if len(line) < 10: continue
                            
                            clean_line = line.replace('|', ' ').replace('!', ' ').replace(']', '1').upper()
                            clean_line = clean_line.replace('O', '0').replace('L', '1').replace('I', '1')

                            date_pattern = r'(\d{1,2})[-/\s.]([A-Z]{3}|\d{1,2})[-/\s.](\d{4})'
                            date_match = re.search(date_pattern, clean_line)
                            
                            if date_match:
                                date_str = date_match.group(0)
                                sem_label = "Unknown"
                                sem_match = re.search(r'(\d+)\s*SEM', clean_line)
                                if sem_match:
                                    sem_label = f"Sem {sem_match.group(1)}"

                                temp = clean_line.replace(date_str, '')
                                temp = re.sub(r'\d+\s*SEM', '', temp)
                                temp = re.sub(r'\b[A-Z0-9]{5,10}\b', '', temp) 
                                temp = temp.replace('MORNING', '').replace('EVENING', '').replace('CSE', '').replace('BRANCH', '').replace('SESSION', '')
                                subject_name = temp.strip()

                                if len(subject_name) > 3 and not subject_name.isdigit():
                                    try:
                                        d_str = date_str.replace('.', '-').replace('/', '-')
                                        try:
                                            exam_date = datetime.strptime(d_str, "%d-%b-%Y")
                                        except:
                                            try:
                                                exam_date = datetime.strptime(d_str, "%d-%B-%Y")
                                            except:
                                                continue 

                                        final_date = timezone.make_aware(datetime(exam_date.year, exam_date.month, exam_date.day, 9, 0))
                                        
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
            # 2. SYLLABUS EXTRACTION (CHO FILES) - UPDATED!
            # ====================================================
            elif title.startswith('CHO') and filename.endswith('.pdf'):
                # CHANGE: Always create a NEW Exam for every CHO file.
                # Use the file Title as the Mission Name.
                # Default date = 30 days from now (User can edit later).
                target_exam = Exam.objects.create(
                    user=request.user, 
                    subject=title,  # Sets name to "CHO DA" etc.
                    date=timezone.now() + timezone.timedelta(days=30),
                    is_datesheet_entry=False # Marks it as a Manual Mission
                )
                messages.success(request, f"Initialized new protocol: {title}")
                
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
                                            Topic.objects.create(
                                                exam=target_exam, 
                                                name=final_name, 
                                                source_note=note, 
                                                is_cho=True
                                            )
                                            extracted_count += 1
                    
                    if extracted_count > 0:
                        messages.success(request, f"⚡ MAPPED {extracted_count} MODULES TO {title}.")

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
        if topic.is_completed: topic.completed_at = timezone.now()
        else: topic.completed_at = None
        topic.save()
        return redirect('topics_hub')
    exams = Exam.objects.filter(user=request.user, is_datesheet_entry=False, topics__is_cho=True).distinct().order_by('date')
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
            if os.path.isfile(note.file.path): os.remove(note.file.path)
        except Exception: pass
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


# ... (Imports remain the same) ...
from .models import Squad, Membership, Transmission # Import new models
from .forms import NoteForm, ExamForm, SquadForm, JoinSquadForm # Import new forms

# ... (Keep existing views) ...

@login_required(login_url='signin')
def squad_hub(request):
    # Get all squads the user belongs to
    my_memberships = Membership.objects.filter(user=request.user)
    my_squads = [m.squad for m in my_memberships]

    create_form = SquadForm()
    join_form = JoinSquadForm()

    if request.method == 'POST':
        # HANDLE CREATE
        if 'create_squad' in request.POST:
            create_form = SquadForm(request.POST)
            if create_form.is_valid():
                squad = create_form.save(commit=False)
                squad.created_by = request.user
                squad.save()
                # Automatically add creator as Leader
                Membership.objects.create(user=request.user, squad=squad, is_leader=True)
                messages.success(request, f"Squadron '{squad.name}' deployed.")
                return redirect('squad_hub')
        
        # HANDLE JOIN
        elif 'join_squad' in request.POST:
            join_form = JoinSquadForm(request.POST)
            if join_form.is_valid():
                code = join_form.cleaned_data['code']
                try:
                    target_squad = Squad.objects.get(code=code)
                    if Membership.objects.filter(user=request.user, squad=target_squad).exists():
                        messages.warning(request, "You are already an operative in this squadron.")
                    else:
                        Membership.objects.create(user=request.user, squad=target_squad)
                        messages.success(request, f"Access granted: {target_squad.name}")
                        return redirect('squad_hub')
                except Squad.DoesNotExist:
                    messages.error(request, "Invalid Access Code.")

    context = {
        'my_squads': my_squads,
        'create_form': create_form,
        'join_form': join_form,
        'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()
    }
    return render(request, 'squad_hub.html', context)

# ... (Keep existing imports) ...

@login_required(login_url='signin')
def squad_detail(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id)
    
    # Security Check: Ensure user is a member
    if not Membership.objects.filter(user=request.user, squad=squad).exists():
        messages.error(request, "Access Denied: You are not an operative of this squadron.")
        return redirect('squad_hub')

    # Handle Chat Message
    if request.method == 'POST' and 'send_transmission' in request.POST:
        content = request.POST.get('content')
        if content:
            Transmission.objects.create(squad=squad, sender=request.user, content=content)
            return redirect('squad_detail', squad_id=squad.id)

    # Get Data
    members = Membership.objects.filter(squad=squad).select_related('user')
    transmissions = squad.messages.all().order_by('timestamp') # Oldest first for chat log

    context = {
        'squad': squad,
        'members': members,
        'transmissions': transmissions,
        'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()
    }
    return render(request, 'squad_detail.html', context)

# Add this under your squad_detail view
@login_required(login_url='signin')
def get_squad_messages(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id)
    # Security check (optional but recommended)
    if not Membership.objects.filter(user=request.user, squad=squad).exists():
        return HttpResponseForbidden()
        
    transmissions = squad.messages.all().order_by('timestamp')
    return render(request, 'partials/chat_messages.html', {'transmissions': transmissions, 'user': request.user})