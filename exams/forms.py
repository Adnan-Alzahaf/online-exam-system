from django import forms
from .models import Exam, Question, SupportTicket


class ExamForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
            format='%Y-%m-%dT%H:%M'
        )
    )

    end_time = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'},
            format='%Y-%m-%dT%H:%M'
        )
    )

    class Meta:
        model = Exam
        fields = [
            'title',
            'subject',
            'subject_ref',
            'department',
            'semester',
            'description',
            'instructions',
            'duration_minutes',
            'passing_marks',
            'attempt_limit',
            'start_time',
            'end_time',
            'exam_code',
            'randomize_questions',
            'randomize_options',
            'is_active',
            'is_published',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'passing_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'attempt_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'exam_code': forms.TextInput(attrs={'class': 'form-control'}),
            'randomize_questions': forms.CheckboxInput(attrs={'class': 'native-check'}),
            'randomize_options': forms.CheckboxInput(attrs={'class': 'native-check'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'native-check'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'native-check'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].widget.attrs.update({'class': 'form-select'})
        self.fields['subject_ref'].widget.attrs.update({'class': 'form-select'})
        self.fields['department'].widget.attrs.update({'class': 'form-select'})
        self.fields['semester'].widget.attrs.update({'class': 'form-select'})
        self.fields['description'].required = False
        self.fields['instructions'].required = False

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        duration_minutes = cleaned_data.get('duration_minutes')

        if start_time and end_time:
            if end_time <= start_time:
                self.add_error('end_time', 'End time must be after start time.')
                return cleaned_data

            if duration_minutes:
                window_seconds = (end_time - start_time).total_seconds()
                window_minutes = window_seconds / 60
                if duration_minutes > window_minutes:
                    self.add_error(
                        'duration_minutes',
                        f'Exam duration ({duration_minutes} min) exceeds the '
                        f'available window ({int(window_minutes)} min between '
                        f'start and end time). Either increase the window or '
                        f'decrease the duration.'
                    )

        return cleaned_data


class QuestionForm(forms.ModelForm):
    question_text = forms.CharField(
        label='Question Text',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    option_a = forms.CharField(
        label='Option A',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    option_b = forms.CharField(
        label='Option B',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    option_c = forms.CharField(
        label='Option C',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    option_d = forms.CharField(
        label='Option D',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    correct_option = forms.ChoiceField(
        label='Correct Option',
        choices=[
            ('', '---------'),
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    marks = forms.IntegerField(
        label='Marks',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Question
        fields = [
            'question_text',
            'option_a',
            'option_b',
            'option_c',
            'option_d',
            'correct_option',
            'marks',
        ]


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }


class AIQuestionGenerationForm(forms.Form):
    pdf_file = forms.FileField(
        label='Course Material (PDF)',
        help_text='Upload a PDF file containing the course content. Maximum 5MB.',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )
    num_questions = forms.IntegerField(
        label='Number of Questions',
        min_value=1,
        max_value=20,
        initial=10,
        help_text='How many questions to generate (1-20).',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '20'})
    )
    total_marks = forms.IntegerField(
        label='Total Marks',
        min_value=1,
        initial=100,
        help_text='Total marks for the exam. Will be distributed equally.',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )

    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            if pdf_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('PDF file too large. Maximum size is 5MB.')
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError('Only PDF files are accepted.')
        return pdf_file