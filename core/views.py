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
import pdfplumber
import re

# ... (Keep signin and dashboard unchanged) ...
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

    if request.method == 'POST' and 'toggle_topic' in request.POST:
        topic_id = request.POST.get('topic_id')
        topic = get_object_or_404(Topic, id=topic_id, exam__user=request.user)
        topic.is_completed = not topic.is_completed
        topic.save()
        return redirect('dashboard')

    upcoming_exams = Exam.objects.filter(user=request.user, date__gte=timezone.now()).order_by('date')
    main_exam = upcoming_exams.first() if upcoming_exams.exists() else None
    
    context = {
        'main_exam': main_exam,
        'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count(),
        'exam_form': ExamForm(),
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

            if note.title.upper().startswith('CHO') and note.file.name.endswith('.pdf'):
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
                                    
                                    # CHECK LECTURE COLUMN (Column 0)
                                    lec_cell = str(row[0]).strip()
                                    if re.match(r'^[\d\s\-]+$', lec_cell):
                                        
                                        # GET TOPIC CONTENT
                                        # Find the cell with the most text
                                        topic_cell = row[1] if row[1] else max(row, key=lambda x: len(str(x)))
                                        topic_text = str(topic_cell).replace('\n', ' ').strip()

                                        if len(topic_text) > 3:
                                            # --- CHANGED LOGIC: ONE ROW = ONE TASK ---
                                            # We do NOT split by comma anymore.
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
                    else:
                        messages.warning(request, "Neural scan complete but no lecture rows identified.")

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
        topic.save()
        return redirect('topics_hub')

    exams = Exam.objects.filter(user=request.user).order_by('date')
    context = {
        'exams': exams,
        'online_count': Profile.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).exclude(user=request.user).count()
    }
    return render(request, 'topics_hub.html', context)

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

# NEW: RENAME EXAM VIEW
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

def home(request):
    return render(request, 'index.html')