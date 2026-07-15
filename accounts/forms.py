'''from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            user.profile.role = self.cleaned_data['role']
            user.profile.save()
        return user'''
'''from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, SEMESTER_CHOICES
from exams.models import Department


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)

    # Optional academic fields (required only for students - validated below)
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="-- Select Department --"
    )
    semester = forms.ChoiceField(
        choices=[('', '-- Select Semester --')] + SEMESTER_CHOICES,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'department', 'semester',
                  'password1', 'password2']

    def clean(self):
        """
        Custom validation:
        - If role is 'student', department and semester are REQUIRED.
        - If role is 'teacher', they are optional and will be ignored.
        """
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        department = cleaned_data.get('department')
        semester = cleaned_data.get('semester')

        if role == 'student':
            if not department:
                self.add_error('department', 'Department is required for students.')
            if not semester:
                self.add_error('semester', 'Semester is required for students.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Update profile with role and academic info
            profile = user.profile
            profile.role = self.cleaned_data['role']

            # Only assign department and semester for students
            if profile.role == 'student':
                profile.department = self.cleaned_data.get('department')
                profile.semester = self.cleaned_data.get('semester')

            profile.save()
        return user'''

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, SEMESTER_CHOICES
from exams.models import Department


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)

    # Optional academic fields (required only for students - validated in clean())
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="-- Select Department --"
    )
    semester = forms.ChoiceField(
        choices=[('', '-- Select Semester --')] + SEMESTER_CHOICES,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'department', 'semester',
                  'password1', 'password2']

    def clean(self):
        """
        Custom validation:
        - If role is 'student', department and semester are REQUIRED.
        - If role is 'teacher', they are optional and will be ignored.
        """
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        department = cleaned_data.get('department')
        semester = cleaned_data.get('semester')

        if role == 'student':
            if not department:
                self.add_error('department', 'Department is required for students.')
            if not semester:
                self.add_error('semester', 'Semester is required for students.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Update profile with role and academic info
            profile = user.profile
            profile.role = self.cleaned_data['role']

            # Only assign department and semester for students
            if profile.role == 'student':
                profile.department = self.cleaned_data.get('department')
                profile.semester = self.cleaned_data.get('semester')

            profile.save()
        return user