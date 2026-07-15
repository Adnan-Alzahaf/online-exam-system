from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserRegisterForm
from .models import Profile
from exams.models import Exam, Result   # ← استيراد جديد لاحظ هنا


def home(request):
    return render(request, 'home.html')


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def teacher_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and hasattr(
            u, 'profile') and u.profile.role == 'teacher'
    )(view_func)


def student_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and hasattr(
            u, 'profile') and u.profile.role == 'student'
    )(view_func)

'''
@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Default statistics (in case role is undefined)
    total_exams = 0
    attempted_exams = 0
    passed_exams = 0
    failed_exams = 0

    # ============================================================
    # Statistics calculation based on user role
    # ============================================================
    if profile.role == 'student':
        # For students: stats reflect their personal exam history
        total_exams = Exam.objects.filter(
            is_active=True,
            is_published=True
        ).count()

        student_results = Result.objects.filter(student=request.user)
        attempted_exams = student_results.count()
        passed_exams = student_results.filter(pass_status=True).count()
        failed_exams = student_results.filter(pass_status=False).count()

    elif profile.role == 'teacher':
        # For teachers: stats reflect their created exams and student performance
        teacher_exams = Exam.objects.filter(teacher=request.user)
        total_exams = teacher_exams.count()

        teacher_results = Result.objects.filter(exam__teacher=request.user)
        attempted_exams = teacher_results.count()
        passed_exams = teacher_results.filter(pass_status=True).count()
        failed_exams = teacher_results.filter(pass_status=False).count()

    context = {
        'profile': profile,
        'total_exams': total_exams,
        'attempted_exams': attempted_exams,
        'passed_exams': passed_exams,
        'failed_exams': failed_exams,
    }

    return render(request, 'accounts/dashboard.html', context)'''

@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Default statistics (in case role is undefined - e.g. superuser without profile.role)
    total_exams = 0
    attempted_exams = 0
    passed_exams = 0
    failed_exams = 0

    # ============================================================
    # Statistics calculation based on user role
    # Logic must MATCH the filtering in /exams/ page exactly
    # ============================================================
    if profile.role == 'student':
        # Student stats: only exams matching their department + semester
        # (matches the filter applied in exams.views.exam_list)
        student_department = profile.department
        student_semester = profile.semester

        if student_department and student_semester:
            total_exams = Exam.objects.filter(
                is_active=True,
                is_published=True,
                department=student_department,
                semester=student_semester
            ).count()
        else:
            # Student didn't set academic info -> no exams visible anywhere
            total_exams = 0

        # Student's personal attempt stats (from Result table)
        student_results = Result.objects.filter(student=request.user)
        attempted_exams = student_results.count()
        passed_exams = student_results.filter(pass_status=True).count()
        failed_exams = student_results.filter(pass_status=False).count()

    elif profile.role == 'teacher':
        # Teacher stats: only exams they created
        # (matches the filter applied in exams.views.exam_list)
        teacher_exams = Exam.objects.filter(teacher=request.user)
        total_exams = teacher_exams.count()

        # Aggregate results across all of teacher's exams
        teacher_results = Result.objects.filter(exam__teacher=request.user)
        attempted_exams = teacher_results.count()
        passed_exams = teacher_results.filter(pass_status=True).count()
        failed_exams = teacher_results.filter(pass_status=False).count()

    context = {
        'profile': profile,
        'total_exams': total_exams,
        'attempted_exams': attempted_exams,
        'passed_exams': passed_exams,
        'failed_exams': failed_exams,
    }

    return render(request, 'accounts/dashboard.html', context)