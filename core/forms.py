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
        
from django import forms
from .models import Note, Exam, Squad

# ... (Keep existing NoteForm / ExamForm) ...

class SquadForm(forms.ModelForm):
    class Meta:
        model = Squad
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:border-emerald-500 outline-none', 'placeholder': 'Squadron Name'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:border-emerald-500 outline-none', 'rows': 3, 'placeholder': 'Mission Parameters'}),
        }

class JoinSquadForm(forms.Form):
    code = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'class': 'w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:border-emerald-500 outline-none', 'placeholder': 'Enter Invite Code (e.g. A7X-99)'}))