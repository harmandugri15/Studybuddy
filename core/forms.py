# studybuddy/studyvault/core/forms.py

from django import forms
from .models import Note, Exam

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'file']

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['subject', 'date']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }