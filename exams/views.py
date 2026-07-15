'''
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Count
from django.shortcuts import render, redirect, get_object_or_404

from .models import Exam, Question, Result, StudentAnswer, ExamAttempt
from .forms import ExamForm, QuestionForm
from accounts.views import teacher_required, student_required


@login_required
def exam_list(request):
    exams = Exam.objects.filter(
        is_active=True,
        is_published=True
    ).order_by('-created_at')

    query = request.GET.get('q')
    subject = request.GET.get('subject')

    if query:
        exams = exams.filter(title__icontains=query)

    if subject:
        exams = exams.filter(subject__icontains=subject)

    subjects = Exam.objects.values_list('subject', flat=True).distinct()

    return render(request, 'exams/exam_list.html', {
        'exams': exams,
        'subjects': subjects,
    })


# @login_required
# @teacher_required
# def exam_create(request):
#     if request.method == 'POST':
#         form = ExamForm(request.POST)
#         if form.is_valid():
#             exam = form.save(commit=False)
#             exam.teacher = request.user
#             exam.save()
#             messages.success(request, 'Exam created successfully.')
#             return redirect('exam_detail', pk=exam.id)
#     else:
#         form = ExamForm()

#     return render(request, 'exams/exam_form.html', {
#         'form': form,
#         'page_title': 'Create Exam'
#     })









@login_required
@teacher_required
def exam_create(request):
    print("METHOD:", request.method)

    if request.method == 'POST':
        print("POST DATA:", request.POST)

        form = ExamForm(request.POST)

        if form.is_valid():
            print("FORM VALID")
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
            print("EXAM SAVED:", exam.id)
            messages.success(request, 'Exam created successfully.')
            return redirect('exam_detail', pk=exam.id)
        else:
            print("FORM INVALID")
            print(form.errors)

    else:
        form = ExamForm()

    return render(request, 'exams/exam_form.html', {
        'form': form,
        'page_title': 'Create Exam'
    })
    
    
    
    

@login_required
@teacher_required
def exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)

    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam updated successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = ExamForm(instance=exam)

    return render(request, 'exams/exam_form.html', {
        'form': form,
        'page_title': 'Update Exam'
    })


@login_required
@teacher_required
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)

    if request.method == 'POST':
        exam.delete()
        messages.success(request, 'Exam deleted successfully.')
        return redirect('exam_list')

    return render(request, 'exams/confirm_delete.html', {
        'object': exam,
        'type': 'Exam'
    })


@login_required
def exam_detail(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    questions = exam.questions.all()
    attempts_used = 0
    attempts_left = exam.attempt_limit

    if hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        attempts_used = Result.objects.filter(
            student=request.user, exam=exam).count()
        attempts_left = max(0, exam.attempt_limit - attempts_used)

    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'questions': questions,
        'attempts_used': attempts_used,
        'attempts_left': attempts_left,
    })


@login_required
@teacher_required
def question_create(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()

            exam.total_marks = sum(q.marks for q in exam.questions.all())
            exam.save()

            messages.success(request, 'Question added successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = QuestionForm()

    return render(request, 'exams/question_form.html', {
        'form': form,
        'exam': exam
    })


@login_required
@teacher_required
def question_update(request, pk):
    question = get_object_or_404(Question, pk=pk, exam__teacher=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()

            exam = question.exam
            exam.total_marks = sum(q.marks for q in exam.questions.all())
            exam.save()

            messages.success(request, 'Question updated successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'exams/question_edit.html', {
        'form': form,
        'question': question
    })


@login_required
@teacher_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk, exam__teacher=request.user)
    exam = question.exam

    if request.method == 'POST':
        question.delete()
        exam.total_marks = sum(q.marks for q in exam.questions.all())
        exam.save()

        messages.success(request, 'Question deleted successfully.')
        return redirect('exam_detail', pk=exam.id)

    return render(request, 'exams/confirm_delete.html', {
        'object': question,
        'type': 'Question'
    })


@login_required
@student_required
def exam_instructions(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
        is_published=True
    )

    attempt_count = Result.objects.filter(
        student=request.user, exam=exam).count()
    attempts_left = exam.attempt_limit - attempt_count

    if attempts_left <= 0:
        messages.error(
            request, 'You have reached the attempt limit for this exam.')
        return redirect('exam_detail', pk=exam.id)

    return render(request, 'exams/exam_instructions.html', {
        'exam': exam,
        'attempts_left': attempts_left,
    })


@login_required
@student_required
def take_exam(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
        is_published=True
    )

    # Randomize question support if field exists
    if hasattr(exam, 'randomize_questions') and exam.randomize_questions:
        questions = exam.questions.all().order_by('?')
    else:
        questions = exam.questions.all()

    attempt_count = Result.objects.filter(
        student=request.user, exam=exam).count()

    if attempt_count >= exam.attempt_limit:
        messages.error(request, 'Attempt limit exceeded for this exam.')
        return redirect('exam_detail', pk=exam.id)

    if request.method == 'POST':
        total = sum(float(q.marks) for q in questions)
        score = 0.0

        result = Result.objects.create(
            student=request.user,
            exam=exam,
            total=total
        )

        ExamAttempt.objects.create(
            student=request.user,
            exam=exam,
            attempt_number=attempt_count + 1
        )

        for question in questions:
            selected = request.POST.get(f'question_{question.id}')
            is_correct = selected == question.correct_option if selected else False

            StudentAnswer.objects.create(
                result=result,
                question=question,
                selected_option=selected if selected else None,
                is_correct=is_correct
            )

            if is_correct:
                score += float(question.marks)
            elif hasattr(exam, 'negative_marking') and exam.negative_marking and selected:
                negative_value = float(
                    getattr(exam, 'negative_marks_per_wrong', 0) or 0)
                score -= negative_value

        score = max(score, 0.0)

        result.score = score
        result.total = total
        result.percentage = round((score / total * 100), 2) if total > 0 else 0

        passing_marks = float(exam.passing_marks or 0)
        result.pass_status = score >= passing_marks

        result.save()

        return redirect('result_detail', pk=result.id)

    return render(request, 'exams/take_exam.html', {
        'exam': exam,
        'questions': questions
    })


@login_required
def result_detail(request, pk):
    result = get_object_or_404(Result, pk=pk)

    if (
        hasattr(request.user, 'profile')
        and request.user.profile.role == 'student'
        and result.student != request.user
    ):
        messages.error(request, 'You are not allowed to view this result.')
        return redirect('result_list')

    answers = result.answers.select_related('question')

    return render(request, 'exams/result_detail.html', {
        'result': result,
        'answers': answers
    })


@login_required
def result_list(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        results = Result.objects.filter(
            student=request.user).order_by('-submitted_at')
    else:
        results = Result.objects.all().order_by('-submitted_at')

    return render(request, 'exams/result_list.html', {
        'results': results
    })


@login_required
@teacher_required
def teacher_analytics(request):
    exams = Exam.objects.filter(teacher=request.user)
    total_exams = exams.count()
    total_questions = Question.objects.filter(
        exam__teacher=request.user).count()
    total_results = Result.objects.filter(exam__teacher=request.user).count()

    stats = Result.objects.filter(exam__teacher=request.user).aggregate(
        avg_score=Avg('percentage'),
        max_score=Max('percentage')
    )

    exam_stats = exams.annotate(student_count=Count('result'))

    return render(request, 'accounts/dashboard.html', {
        'profile': request.user.profile,
        'analytics': True,
        'total_exams': total_exams,
        'total_questions': total_questions,
        'total_results': total_results,
        'avg_score': stats['avg_score'] or 0,
        'max_score': stats['max_score'] or 0,
        'exam_stats': exam_stats,
    })


@login_required
def books_page(request):
    books = [
        {
            "title": "Python Programming Handbook",
            "subject": "Python",
            "desc": "Core concepts, syntax, MCQ prep, functions, OOP, and practice notes.",
            "type": "PDF Notes",
            "level": "Beginner to Intermediate",
        },
        {
            "title": "Database Management System Notes",
            "subject": "DBMS",
            "desc": "ER model, normalization, SQL, transactions, and repeated exam topics.",
            "type": "Theory + MCQ",
            "level": "Semester Prep",
        },
        {
            "title": "Operating System Revision Guide",
            "subject": "OS",
            "desc": "Process, scheduling, memory management, deadlock, and short questions.",
            "type": "Revision Sheet",
            "level": "Exam Ready",
        },
        {
            "title": "Computer Networks Quick Notes",
            "subject": "CN",
            "desc": "OSI model, TCP/IP, routing, switching, protocols, and viva questions.",
            "type": "Short Notes",
            "level": "Fast Revision",
        },
        {
            "title": "Data Structures Complete Notes",
            "subject": "DSA",
            "desc": "Stack, queue, linked list, tree, graph, sorting, and complexity basics.",
            "type": "Concept Book",
            "level": "Practice Oriented",
        },
        {
            "title": "Software Engineering Essentials",
            "subject": "SE",
            "desc": "SDLC, testing, models, design basics, project flow, and important theory.",
            "type": "Exam Notes",
            "level": "University Use",
        },

        {"title": "Advanced Python Notes", "subject": "Python",
            "desc": "Decorators, generators, OOP deep concepts.", "type": "Notes", "level": "Advanced"},
        {"title": "DBMS Complete Guide", "subject": "DBMS",
            "desc": "Normalization, SQL, transactions.", "type": "PDF", "level": "Intermediate"},
        {"title": "Operating System Concepts", "subject": "OS",
            "desc": "Process, memory, scheduling.", "type": "Theory", "level": "Core"},
        {"title": "Computer Networks Basics", "subject": "CN",
            "desc": "OSI, TCP/IP, protocols.", "type": "Notes", "level": "Beginner"},
        {"title": "Data Structures in C", "subject": "DSA",
            "desc": "Stack, Queue, Linked List.", "type": "Practice", "level": "Core"},
        {"title": "Java Programming", "subject": "Java",
            "desc": "OOP, multithreading, collections.", "type": "PDF", "level": "Intermediate"},
        {"title": "Software Engineering", "subject": "SE",
            "desc": "SDLC, Agile, Testing.", "type": "Notes", "level": "Exam"},
        {"title": "Web Development Basics", "subject": "Web",
            "desc": "HTML, CSS, JS fundamentals.", "type": "Guide", "level": "Beginner"},
        {"title": "Django Full Guide", "subject": "Django",
            "desc": "Models, views, templates.", "type": "Framework", "level": "Intermediate"},
        {"title": "Machine Learning Intro", "subject": "ML",
            "desc": "Supervised & unsupervised learning.", "type": "PDF", "level": "Basic"},
        {"title": "Artificial Intelligence", "subject": "AI",
            "desc": "Search, reasoning, ML basics.", "type": "Theory", "level": "Intermediate"},
        {"title": "Cyber Security Basics", "subject": "Security",
            "desc": "Encryption, attacks, defense.", "type": "Guide", "level": "Beginner"},
        {"title": "Cloud Computing", "subject": "Cloud",
            "desc": "AWS, Azure basics.", "type": "Notes", "level": "Intermediate"},
        {"title": "Linux Essentials", "subject": "OS",
            "desc": "Commands, shell scripting.", "type": "Practice", "level": "Beginner"},
        {"title": "C Programming", "subject": "C",
            "desc": "Pointers, memory, basics.", "type": "PDF", "level": "Core"},
        {"title": "C++ OOP Concepts", "subject": "C++",
            "desc": "Classes, inheritance, polymorphism.", "type": "Notes", "level": "Intermediate"},
        {"title": "Digital Electronics", "subject": "DE",
            "desc": "Logic gates, circuits.", "type": "Theory", "level": "Core"},
        {"title": "Compiler Design", "subject": "CD",
            "desc": "Parsing, lexical analysis.", "type": "Advanced", "level": "Advanced"},


    ]

    return render(request, 'exams/books.html', {
        'books': books
    })


@login_required
def pyq_page(request):
    pyqs = [
        {
            "title": "Python PYQ 2024",
            "subject": "Python",
            "year": "2024",
            "desc": "Important MCQs, output questions, and practical-oriented repeated patterns.",
            "paper_type": "Previous Year Paper",
        },
        {
            "title": "DBMS PYQ 2023",
            "subject": "DBMS",
            "year": "2023",
            "desc": "Normalization, SQL queries, transaction-based descriptive and short questions.",
            "paper_type": "University Questions",
        },
        {
            "title": "Operating System PYQ 2022",
            "subject": "OS",
            "year": "2022",
            "desc": "Process scheduling, paging, deadlock, synchronization, and long-answer topics.",
            "paper_type": "Semester Paper",
        },
        {
            "title": "Computer Networks PYQ 2021",
            "subject": "CN",
            "year": "2021",
            "desc": "Layer-based theory, routing algorithms, switching, and short viva questions.",
            "paper_type": "Final Exam Paper",
        },
        {
            "title": "Software Engineering PYQ 2023",
            "subject": "SE",
            "year": "2023",
            "desc": "SDLC, testing, design models, requirement engineering, and software lifecycle.",
            "paper_type": "Question Bank",
        },
        {
            "title": "Data Structures PYQ 2024",
            "subject": "DSA",
            "year": "2024",
            "desc": "Array, stack, queue, tree, graph, searching, sorting, and algorithm basics.",
            "paper_type": "Important Set",
        },
    ]

    return render(request, 'exams/pyq.html', {
        'pyqs': pyqs
    })


@login_required
def support_page(request):
    support_items = [
        {
            "title": "Exam Guidelines",
            "icon": "bi-shield-check",
            "desc": "Read all important rules before starting any online examination.",
        },
        {
            "title": "Student Help Desk",
            "icon": "bi-headset",
            "desc": "Get support for login issues, exam access problems, and submission doubts.",
        },
        {
            "title": "Download Resources",
            "icon": "bi-download",
            "desc": "Access useful PDFs, revision sheets, sample patterns, and academic support files.",
        },
        {
            "title": "Teacher Support",
            "icon": "bi-person-workspace",
            "desc": "Teachers can manage exams, add questions, and review student performance.",
        },
        {
            "title": "Technical Help",
            "icon": "bi-tools",
            "desc": "Troubleshoot browser, device, internet, and dark mode related issues.",
        },
        {
            "title": "Academic FAQ",
            "icon": "bi-patch-question",
            "desc": "Get answers to common questions about exams, attempts, results, and resources.",
        },
    ]

    return render(request, 'exams/support.html', {
        'support_items': support_items
    })
'''

# ============================================================
# TAKE EXAM (core grading logic)
# ============================================================
'''@login_required
@student_required
def take_exam(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
        is_published=True
    )

    # Randomize question support if field exists
    if hasattr(exam, 'randomize_questions') and exam.randomize_questions:
        questions = exam.questions.all().order_by('?')
    else:
        questions = exam.questions.all()

    attempt_count = Result.objects.filter(
        student=request.user, exam=exam).count()

    if attempt_count >= exam.attempt_limit:
        messages.error(request, 'Attempt limit exceeded for this exam.')
        return redirect('exam_detail', pk=exam.id)

    if request.method == 'POST':
        total = sum(float(q.marks) for q in questions)
        score = 0.0

        result = Result.objects.create(
            student=request.user,
            exam=exam,
            total=total
        )

        ExamAttempt.objects.create(
            student=request.user,
            exam=exam,
            attempt_number=attempt_count + 1
        )

        for question in questions:
            selected = request.POST.get(f'question_{question.id}')
            is_correct = selected == question.correct_option if selected else False

            StudentAnswer.objects.create(
                result=result,
                question=question,
                selected_option=selected if selected else None,
                is_correct=is_correct
            )

            if is_correct:
                score += float(question.marks)
            elif hasattr(exam, 'negative_marking') and exam.negative_marking and selected:
                negative_value = float(
                    getattr(exam, 'negative_marks_per_wrong', 0) or 0)
                score -= negative_value

        score = max(score, 0.0)

        result.score = score
        result.total = total
        result.percentage = round((score / total * 100), 2) if total > 0 else 0

        passing_marks = float(exam.passing_marks or 0)
        result.pass_status = score >= passing_marks

        result.save()

        return redirect('result_detail', pk=result.id)

    return render(request, 'exams/take_exam.html', {
        'exam': exam,
        'questions': questions
    })
'''

# ============================================================
# TAKE EXAM (core grading logic + shuffling engine)
# ============================================================
# ============================================================
# TAKE EXAM (with Server-Side Timer + Refresh protection)
# ============================================================
import random
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Count
from django.shortcuts import render, redirect, get_object_or_404

from .models import Exam, Question, Result, StudentAnswer, ExamAttempt
from .forms import ExamForm, QuestionForm
from accounts.views import teacher_required, student_required

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
# ============================================================
# EXAM LIST - Role-based filtering
# ============================================================
@login_required
def exam_list(request):
    """
    Show exams filtered by user role:
    - Teachers: see only exams they created (all statuses)
    - Students: see only exams matching their department + semester
    - Others (admin/no profile): see nothing (use /admin/ instead)
    """
    user = request.user
    has_profile = hasattr(user, 'profile')

    if has_profile and user.profile.role == 'teacher':
        exams = Exam.objects.filter(teacher=user).order_by('-created_at')

    elif has_profile and user.profile.role == 'student':
        student_department = user.profile.department
        student_semester = user.profile.semester

        if not student_department or not student_semester:
            exams = Exam.objects.none()
        else:
            exams = Exam.objects.filter(
                is_active=True,
                is_published=True,
                department=student_department,
                semester=student_semester
            ).order_by('-created_at')

    else:
        exams = Exam.objects.none()

    query = request.GET.get('q')
    subject = request.GET.get('subject')

    if query:
        exams = exams.filter(title__icontains=query)

    if subject:
        exams = exams.filter(subject__icontains=subject)

    subjects = exams.values_list('subject', flat=True).distinct()

    return render(request, 'exams/exam_list.html', {
        'exams': exams,
        'subjects': subjects,
    })


# ============================================================
# EXAM CREATE
# ============================================================
@login_required
@teacher_required
def exam_create(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
            messages.success(request, 'Exam created successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = ExamForm()

    return render(request, 'exams/exam_form.html', {
        'form': form,
        'page_title': 'Create Exam'
    })


# ============================================================
# EXAM UPDATE
# ============================================================
@login_required
@teacher_required
def exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)

    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam updated successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = ExamForm(instance=exam)

    return render(request, 'exams/exam_form.html', {
        'form': form,
        'page_title': 'Update Exam'
    })


# ============================================================
# EXAM DELETE
# ============================================================
@login_required
@teacher_required
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk, teacher=request.user)

    if request.method == 'POST':
        exam.delete()
        messages.success(request, 'Exam deleted successfully.')
        return redirect('exam_list')

    return render(request, 'exams/confirm_delete.html', {
        'object': exam,
        'type': 'Exam'
    })


# ============================================================
# EXAM DETAIL
# ============================================================
@login_required
def exam_detail(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    questions = exam.questions.all()
    attempts_used = 0
    attempts_left = exam.attempt_limit

    if hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        attempts_used = Result.objects.filter(
            student=request.user, exam=exam).count()
        attempts_left = max(0, exam.attempt_limit - attempts_used)

    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'questions': questions,
        'attempts_used': attempts_used,
        'attempts_left': attempts_left,
    })


# ============================================================
# QUESTION CREATE
# ============================================================
@login_required
@teacher_required
def question_create(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()

            exam.total_marks = sum(q.marks for q in exam.questions.all())
            exam.save()

            messages.success(request, 'Question added successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = QuestionForm()

    return render(request, 'exams/question_form.html', {
        'form': form,
        'exam': exam
    })


# ============================================================
# QUESTION UPDATE
# ============================================================
@login_required
@teacher_required
def question_update(request, pk):
    question = get_object_or_404(Question, pk=pk, exam__teacher=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()

            exam = question.exam
            exam.total_marks = sum(q.marks for q in exam.questions.all())
            exam.save()

            messages.success(request, 'Question updated successfully.')
            return redirect('exam_detail', pk=exam.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'exams/question_edit.html', {
        'form': form,
        'question': question
    })


# ============================================================
# QUESTION DELETE
# ============================================================
@login_required
@teacher_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk, exam__teacher=request.user)
    exam = question.exam

    if request.method == 'POST':
        question.delete()
        exam.total_marks = sum(q.marks for q in exam.questions.all())
        exam.save()

        messages.success(request, 'Question deleted successfully.')
        return redirect('exam_detail', pk=exam.id)

    return render(request, 'exams/confirm_delete.html', {
        'object': question,
        'type': 'Question'
    })


# ============================================================
# EXAM INSTRUCTIONS (with start/end time validation)
# ============================================================
@login_required
@student_required
def exam_instructions(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
        is_published=True
    )

    now = timezone.now()

    if exam.start_time and now < exam.start_time:
        messages.error(
            request,
            f'This exam is not available yet. It opens at '
            f'{timezone.localtime(exam.start_time).strftime("%Y-%m-%d %H:%M")}.'
        )
        return redirect('exam_detail', pk=exam.id)

    if exam.end_time and now > exam.end_time:
        messages.error(
            request,
            f'This exam is closed. It ended at '
            f'{timezone.localtime(exam.end_time).strftime("%Y-%m-%d %H:%M")}.'
        )
        return redirect('exam_detail', pk=exam.id)

    attempt_count = Result.objects.filter(
        student=request.user, exam=exam).count()
    attempts_left = exam.attempt_limit - attempt_count

    if attempts_left <= 0:
        messages.error(
            request, 'You have reached the attempt limit for this exam.')
        return redirect('exam_detail', pk=exam.id)

    return render(request, 'exams/exam_instructions.html', {
        'exam': exam,
        'attempts_left': attempts_left,
    })


# ============================================================
# TAKE EXAM (with Server-Side Timer + Refresh protection)
# ============================================================
@login_required
@student_required
def take_exam(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
        is_published=True
    )

    now = timezone.now()

    # Pre-checks: start_time, end_time, attempt limit
    if exam.start_time and now < exam.start_time:
        messages.error(
            request,
            f'This exam is not available yet. It opens at '
            f'{timezone.localtime(exam.start_time).strftime("%Y-%m-%d %H:%M")}.'
        )
        return redirect('exam_detail', pk=exam.id)

    if exam.end_time and now > exam.end_time:
        messages.error(
            request,
            f'This exam is closed. It ended at '
            f'{timezone.localtime(exam.end_time).strftime("%Y-%m-%d %H:%M")}.'
        )
        return redirect('exam_detail', pk=exam.id)

    attempt_count = Result.objects.filter(
        student=request.user, exam=exam).count()

    if attempt_count >= exam.attempt_limit:
        messages.error(request, 'Attempt limit exceeded for this exam.')
        return redirect('exam_detail', pk=exam.id)

    current_attempt_number = attempt_count + 1

    # Server-Side Timer: get_or_create preserves started_at on refresh
    attempt, attempt_created = ExamAttempt.objects.get_or_create(
        student=request.user,
        exam=exam,
        attempt_number=current_attempt_number,
        defaults={'started_at': now}
    )

    # Calculate remaining seconds
    elapsed_seconds = (now - attempt.started_at).total_seconds()
    total_seconds = exam.duration_minutes * 60
    remaining_seconds = int(total_seconds - elapsed_seconds)

    # Also enforce the exam end_time as an upper bound
    if exam.end_time:
        seconds_to_end_time = int((exam.end_time - now).total_seconds())
        remaining_seconds = min(remaining_seconds, seconds_to_end_time)

    # If time is already up, auto-submit
    if remaining_seconds <= 0 and request.method != 'POST':
        messages.warning(
            request,
            'Your time has expired. The exam has been auto-submitted.'
        )
        return _auto_submit_empty(request, exam, attempt, current_attempt_number)

    # Module 2: Question Shuffling
    seed_value = f"{request.user.id}-{exam.id}-{current_attempt_number}"
    questions = list(exam.questions.all())

    if exam.randomize_questions:
        rng = random.Random(seed_value)
        rng.shuffle(questions)

    if exam.randomize_options:
        for q in questions:
            q_seed = f"{seed_value}-q{q.id}"
            q_rng = random.Random(q_seed)
            original_options = [
                ('A', q.option_a),
                ('B', q.option_b),
                ('C', q.option_c),
                ('D', q.option_d),
            ]
            q_rng.shuffle(original_options)
            q.shuffled_options = original_options
            q.display_to_original = {
                'A': original_options[0][0],
                'B': original_options[1][0],
                'C': original_options[2][0],
                'D': original_options[3][0],
            }
    else:
        for q in questions:
            q.shuffled_options = [
                ('A', q.option_a),
                ('B', q.option_b),
                ('C', q.option_c),
                ('D', q.option_d),
            ]
            q.display_to_original = {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'}

    # POST: Grade the submission
    if request.method == 'POST':
        return _grade_submission(
            request, exam, questions, attempt, current_attempt_number
        )

    return render(request, 'exams/take_exam.html', {
        'exam': exam,
        'questions': questions,
        'remaining_seconds': max(remaining_seconds, 0),
    })


# ============================================================
# Helper: Grade a submitted exam
# ============================================================
def _grade_submission(request, exam, questions, attempt, attempt_number):
    """Grades the POSTed answers and creates a Result."""
    total = sum(float(q.marks) for q in questions)
    score = 0.0

    result = Result.objects.create(
        student=request.user,
        exam=exam,
        total=total
    )

    for question in questions:
        displayed_selected = request.POST.get(f'question_{question.id}')

        if displayed_selected:
            actual_selected = question.display_to_original.get(
                displayed_selected, displayed_selected
            )
        else:
            actual_selected = None

        is_correct = (
            actual_selected == question.correct_option
            if actual_selected else False
        )

        StudentAnswer.objects.create(
            result=result,
            question=question,
            selected_option=actual_selected,
            is_correct=is_correct
        )

        if is_correct:
            score += float(question.marks)

    score = max(score, 0.0)
    result.score = score
    result.total = total
    result.percentage = round((score / total * 100), 2) if total > 0 else 0
    result.pass_status = score >= float(exam.passing_marks or 0)
    result.save()

    return redirect('result_detail', pk=result.id)


# ============================================================
# Helper: Auto-submit empty exam when time expires before POST
# ============================================================
def _auto_submit_empty(request, exam, attempt, attempt_number):
    """Creates a Result with 0 score - used when time runs out without submission."""
    total = sum(float(q.marks) for q in exam.questions.all())

    result = Result.objects.create(
        student=request.user,
        exam=exam,
        total=total,
        score=0,
        percentage=0,
        pass_status=False
    )

    for question in exam.questions.all():
        StudentAnswer.objects.create(
            result=result,
            question=question,
            selected_option=None,
            is_correct=False
        )

    return redirect('result_detail', pk=result.id)


# ============================================================
# RESULT DETAIL
# ============================================================
@login_required
def result_detail(request, pk):
    result = get_object_or_404(Result, pk=pk)

    if (
        hasattr(request.user, 'profile')
        and request.user.profile.role == 'student'
        and result.student != request.user
    ):
        messages.error(request, 'You are not allowed to view this result.')
        return redirect('result_list')

    answers = result.answers.select_related('question')

    return render(request, 'exams/result_detail.html', {
        'result': result,
        'answers': answers
    })


# ============================================================
# RESULT LIST
# ============================================================
@login_required
def result_list(request):
    if hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        results = Result.objects.filter(
            student=request.user).order_by('-submitted_at')
    else:
        results = Result.objects.all().order_by('-submitted_at')

    return render(request, 'exams/result_list.html', {
        'results': results
    })


# ============================================================
# TEACHER ANALYTICS
# ============================================================
@login_required
@teacher_required
def teacher_analytics(request):
    exams = Exam.objects.filter(teacher=request.user)
    total_exams = exams.count()
    total_questions = Question.objects.filter(
        exam__teacher=request.user).count()
    total_results = Result.objects.filter(exam__teacher=request.user).count()

    stats = Result.objects.filter(exam__teacher=request.user).aggregate(
        avg_score=Avg('percentage'),
        max_score=Max('percentage')
    )

    exam_stats = exams.annotate(student_count=Count('result'))

    return render(request, 'accounts/dashboard.html', {
        'profile': request.user.profile,
        'analytics': True,
        'total_exams': total_exams,
        'total_questions': total_questions,
        'total_results': total_results,
        'avg_score': stats['avg_score'] or 0,
        'max_score': stats['max_score'] or 0,
        'exam_stats': exam_stats,
    })


# ============================================================
# STATIC PAGES: Books, PYQ, Support
# ============================================================
@login_required
def books_page(request):
    books = [
        {"title": "Python Programming Handbook", "subject": "Python",
            "desc": "Core concepts, syntax, MCQ prep.", "type": "PDF Notes", "level": "Beginner"},
        {"title": "Database Management Notes", "subject": "DBMS",
            "desc": "ER model, normalization, SQL.", "type": "Theory + MCQ", "level": "Semester"},
        {"title": "Operating System Guide", "subject": "OS",
            "desc": "Process, scheduling, memory.", "type": "Revision Sheet", "level": "Exam Ready"},
        {"title": "Computer Networks Notes", "subject": "CN",
            "desc": "OSI model, TCP/IP, routing.", "type": "Short Notes", "level": "Fast Revision"},
        {"title": "Data Structures Notes", "subject": "DSA",
            "desc": "Stack, queue, linked list, tree.", "type": "Concept Book", "level": "Practice"},
        {"title": "Software Engineering Essentials", "subject": "SE",
            "desc": "SDLC, testing, design.", "type": "Exam Notes", "level": "University"},
        {"title": "Java Programming", "subject": "Java",
            "desc": "OOP, multithreading.", "type": "PDF", "level": "Intermediate"},
        {"title": "Django Full Guide", "subject": "Django",
            "desc": "Models, views, templates.", "type": "Framework", "level": "Intermediate"},
        {"title": "Machine Learning Intro", "subject": "ML",
            "desc": "Supervised & unsupervised.", "type": "PDF", "level": "Basic"},
        {"title": "Artificial Intelligence", "subject": "AI",
            "desc": "Search, reasoning, ML.", "type": "Theory", "level": "Intermediate"},
        {"title": "Cyber Security Basics", "subject": "Security",
            "desc": "Encryption, attacks, defense.", "type": "Guide", "level": "Beginner"},
        {"title": "Cloud Computing", "subject": "Cloud",
            "desc": "AWS, Azure basics.", "type": "Notes", "level": "Intermediate"},
    ]

    return render(request, 'exams/books.html', {'books': books})


@login_required
def pyq_page(request):
    pyqs = [
        {"title": "Python PYQ 2024", "subject": "Python", "year": "2024",
            "desc": "Important MCQs and patterns.", "paper_type": "Previous Year"},
        {"title": "DBMS PYQ 2023", "subject": "DBMS", "year": "2023",
            "desc": "Normalization, SQL queries.", "paper_type": "University Questions"},
        {"title": "OS PYQ 2022", "subject": "OS", "year": "2022",
            "desc": "Process scheduling, paging.", "paper_type": "Semester Paper"},
        {"title": "CN PYQ 2021", "subject": "CN", "year": "2021",
            "desc": "Layer theory, routing.", "paper_type": "Final Exam"},
        {"title": "SE PYQ 2023", "subject": "SE", "year": "2023",
            "desc": "SDLC, testing, design.", "paper_type": "Question Bank"},
        {"title": "DSA PYQ 2024", "subject": "DSA", "year": "2024",
            "desc": "Array, stack, tree, graph.", "paper_type": "Important Set"},
    ]

    return render(request, 'exams/pyq.html', {'pyqs': pyqs})


@login_required
def support_page(request):
    support_items = [
        {"title": "Exam Guidelines", "icon": "bi-shield-check",
            "desc": "Important rules before starting any exam."},
        {"title": "Student Help Desk", "icon": "bi-headset",
            "desc": "Support for login and submission issues."},
        {"title": "Download Resources", "icon": "bi-download",
            "desc": "PDFs, revision sheets, sample patterns."},
        {"title": "Teacher Support", "icon": "bi-person-workspace",
            "desc": "Manage exams, add questions, review."},
        {"title": "Technical Help", "icon": "bi-tools",
            "desc": "Troubleshoot browser, device, network."},
        {"title": "Academic FAQ", "icon": "bi-patch-question",
            "desc": "Common questions about exams."},
    ]

    return render(request, 'exams/support.html', {'support_items': support_items})

# ============================================================
# Helper: Register Arabic font (once at module load)
# ============================================================
_arabic_font_registered = False


def _register_arabic_font():
    """Register Amiri font (or fallback to Arial) for Arabic support."""
    global _arabic_font_registered
    if _arabic_font_registered:
        return

    font_candidates = [
        (
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Amiri-Regular.ttf'),
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Amiri-Bold.ttf'),
        ),
        (
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/arialbd.ttf',
        ),
    ]

    for regular_path, bold_path in font_candidates:
        if os.path.exists(regular_path):
            try:
                pdfmetrics.registerFont(TTFont('ArabicFont', regular_path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont('ArabicFont-Bold', bold_path))
                else:
                    pdfmetrics.registerFont(TTFont('ArabicFont-Bold', regular_path))
                _arabic_font_registered = True
                return
            except Exception:
                continue


def _ar(text):
    """Process text for Arabic display in reportlab."""
    if text is None:
        return '-'
    text = str(text)
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text
# ============================================================
# RESULT PDF DOWNLOAD (Module 4: PDF Certificate Generation)
# ============================================================
@login_required
@student_required
# ============================================================
# RESULT PDF DOWNLOAD (Module 4: PDF Certificate Generation)
# Now with Arabic font support!
# ============================================================
@login_required
@student_required
def result_pdf(request, pk):
    """
    Generate a PDF certificate + detailed report for a single result.
    Supports Arabic text via Amiri/Arial font + arabic-reshaper + python-bidi.
    """
    result = get_object_or_404(Result, pk=pk, student=request.user)
    exam = result.exam
    answers = result.answers.select_related('question').all()

    # Register Arabic-capable font
    _register_arabic_font()
    arabic_font = 'ArabicFont'
    arabic_font_bold = 'ArabicFont-Bold'

    # Create the PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=arabic_font_bold,
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontName=arabic_font,
        fontSize=14,
        textColor=colors.HexColor('#7f8c8d'),
        alignment=TA_CENTER,
        spaceAfter=30,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=arabic_font_bold,
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
    )

    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontName=arabic_font_bold,
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=4,
        leftIndent=10,
    )

    option_style = ParagraphStyle(
        'Option',
        parent=styles['Normal'],
        fontName=arabic_font,
        fontSize=10,
        leftIndent=25,
        spaceAfter=3,
    )

    story = []

    # --- HEADER ---
    story.append(Paragraph("ExamSphere", title_style))
    story.append(Paragraph("Exam Result Certificate", subtitle_style))
    story.append(Spacer(1, 0.3*cm))

    # --- STUDENT & EXAM INFO TABLE ---
    info_data = [
        ['Student Name:', _ar(request.user.username)],
        ['Exam Title:', _ar(exam.title)],
        ['Subject:', _ar(exam.subject) if exam.subject else '-'],
        ['Department:', _ar(exam.department.name) if exam.department else '-'],
        ['Semester:', f"Semester {exam.semester}" if exam.semester else '-'],
        ['Teacher:', _ar(exam.teacher.username) if exam.teacher else '-'],
        ['Date:', timezone.localtime(result.submitted_at).strftime('%Y-%m-%d %H:%M')],
    ]

    info_table = Table(info_data, colWidths=[5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), arabic_font_bold),
        ('FONTNAME', (1, 0), (1, -1), arabic_font),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#ecf0f1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # --- RESULT SUMMARY ---
    story.append(Paragraph("Result Summary", heading_style))

    pass_status = "PASS" if result.pass_status else "FAIL"
    pass_color = colors.HexColor('#27ae60') if result.pass_status else colors.HexColor('#e74c3c')

    summary_data = [
        ['Score:', f"{result.score} / {result.total}"],
        ['Percentage:', f"{result.percentage}%"],
        ['Passing Marks:', f"{exam.passing_marks or 0}"],
        ['Status:', pass_status],
    ]

    summary_table = Table(summary_data, colWidths=[5*cm, 11*cm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), arabic_font_bold),
        ('FONTNAME', (1, 0), (1, -1), arabic_font),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (1, 0), (1, -2), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (1, -1), (1, -1), pass_color),
        ('FONTNAME', (1, -1), (1, -1), arabic_font_bold),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#ecf0f1')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.8*cm))

    # --- QUESTIONS REVIEW ---
    story.append(Paragraph("Questions Review", heading_style))

    for idx, answer in enumerate(answers, start=1):
        question = answer.question

        story.append(Paragraph(
            f"Q{idx}. {_ar(question.question_text)}",
            question_style
        ))

        options = [
            ('A', question.option_a),
            ('B', question.option_b),
            ('C', question.option_c),
            ('D', question.option_d),
        ]

        for letter, text in options:
            marker = ""
            color_attr = ""

            if letter == question.correct_option:
                marker = " (Correct Answer)"
                color_attr = '#27ae60'
            if letter == answer.selected_option and letter != question.correct_option:
                marker = " (Your Answer)"
                color_attr = '#e74c3c'
            elif letter == answer.selected_option and letter == question.correct_option:
                marker = " (Your Correct Answer)"

            display_text = _ar(text)

            if color_attr:
                option_text = f'<font color="{color_attr}"><b>{letter}.</b> {display_text}{marker}</font>'
            else:
                option_text = f'<b>{letter}.</b> {display_text}{marker}'

            story.append(Paragraph(option_text, option_style))

        if answer.selected_option is None:
            status_text = '<font color="#95a5a6"><i>Status: Not Answered</i></font>'
        elif answer.is_correct:
            status_text = '<font color="#27ae60"><b>Status: Correct</b></font>'
        else:
            status_text = '<font color="#e74c3c"><b>Status: Incorrect</b></font>'

        status_para = ParagraphStyle(
            'Status',
            parent=styles['Normal'],
            fontName=arabic_font,
            fontSize=10,
            leftIndent=25,
            spaceAfter=12,
            spaceBefore=4,
        )
        story.append(Paragraph(status_text, status_para))

    # --- FOOTER ---
    story.append(Spacer(1, 1*cm))

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=arabic_font,
        fontSize=9,
        textColor=colors.HexColor('#95a5a6'),
        alignment=TA_CENTER,
    )
    story.append(Paragraph(
        f"Generated by ExamSphere on {timezone.localtime().strftime('%Y-%m-%d %H:%M')}",
        footer_style
    ))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    safe_exam_title = "".join(c for c in exam.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_exam_title = safe_exam_title.replace(' ', '_') or 'Result'
    filename = f"Result_{safe_exam_title}_{result.submitted_at.strftime('%Y%m%d')}.pdf"

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response

    # ============================================================
    # Styles
    # ============================================================
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#7f8c8d'),
        alignment=TA_CENTER,
        spaceAfter=30,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
    )

    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=4,
        leftIndent=10,
        fontName='Helvetica-Bold',
    )

    option_style = ParagraphStyle(
        'Option',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=25,
        spaceAfter=3,
    )

    # ============================================================
    # Build PDF content
    # ============================================================
    story = []

    # --- HEADER ---
    story.append(Paragraph("ExamSphere", title_style))
    story.append(Paragraph("Exam Result Certificate", subtitle_style))
    story.append(Spacer(1, 0.3*cm))

    # --- STUDENT & EXAM INFO TABLE ---
    info_data = [
        ['Student Name:', request.user.username],
        ['Exam Title:', exam.title],
        ['Subject:', exam.subject or '-'],
        ['Department:', exam.department.name if exam.department else '-'],
        ['Semester:', f"Semester {exam.semester}" if exam.semester else '-'],
        ['Teacher:', exam.teacher.username if exam.teacher else '-'],
        ['Date:', timezone.localtime(result.submitted_at).strftime('%Y-%m-%d %H:%M')],
    ]

    info_table = Table(info_data, colWidths=[5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#ecf0f1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # --- RESULT SUMMARY ---
    story.append(Paragraph("Result Summary", heading_style))

    pass_status = "PASS" if result.pass_status else "FAIL"
    pass_color = colors.HexColor('#27ae60') if result.pass_status else colors.HexColor('#e74c3c')

    summary_data = [
        ['Score:', f"{result.score} / {result.total}"],
        ['Percentage:', f"{result.percentage}%"],
        ['Passing Marks:', f"{exam.passing_marks or 0}"],
        ['Status:', pass_status],
    ]

    summary_table = Table(summary_data, colWidths=[5*cm, 11*cm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (1, 0), (1, -2), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (1, -1), (1, -1), pass_color),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#ecf0f1')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.8*cm))

    # --- QUESTIONS REVIEW ---
    story.append(Paragraph("Questions Review", heading_style))

    for idx, answer in enumerate(answers, start=1):
        question = answer.question

        # Question text
        story.append(Paragraph(
            f"Q{idx}. {question.question_text}",
            question_style
        ))

        # Options
        options = [
            ('A', question.option_a),
            ('B', question.option_b),
            ('C', question.option_c),
            ('D', question.option_d),
        ]

        for letter, text in options:
            marker = ""
            color_attr = ""

            if letter == question.correct_option:
                marker = " ✓ (Correct Answer)"
                color_attr = '#27ae60'  # green
            if letter == answer.selected_option and letter != question.correct_option:
                marker = " ✗ (Your Answer)"
                color_attr = '#e74c3c'  # red
            elif letter == answer.selected_option and letter == question.correct_option:
                marker = " ✓ (Your Correct Answer)"

            if color_attr:
                option_text = f'<font color="{color_attr}"><b>{letter}.</b> {text}{marker}</font>'
            else:
                option_text = f'<b>{letter}.</b> {text}{marker}'

            story.append(Paragraph(option_text, option_style))

        # Result indicator
        if answer.selected_option is None:
            status_text = '<font color="#95a5a6"><i>Status: Not Answered</i></font>'
        elif answer.is_correct:
            status_text = '<font color="#27ae60"><b>Status: Correct</b></font>'
        else:
            status_text = '<font color="#e74c3c"><b>Status: Incorrect</b></font>'

        status_para = ParagraphStyle(
            'Status',
            parent=styles['Normal'],
            fontSize=10,
            leftIndent=25,
            spaceAfter=12,
            spaceBefore=4,
        )
        story.append(Paragraph(status_text, status_para))

    # --- FOOTER ---
    story.append(Spacer(1, 1*cm))

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#95a5a6'),
        alignment=TA_CENTER,
    )
    story.append(Paragraph(
        f"Generated by ExamSphere on {timezone.localtime().strftime('%Y-%m-%d %H:%M')}",
        footer_style
    ))

    # ============================================================
    # Build PDF
    # ============================================================
    doc.build(story)

    # Get the PDF data
    pdf = buffer.getvalue()
    buffer.close()

    # Create HTTP response
    safe_exam_title = "".join(c for c in exam.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_exam_title = safe_exam_title.replace(' ', '_')
    filename = f"Result_{safe_exam_title}_{result.submitted_at.strftime('%Y%m%d')}.pdf"

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response

    # ============================================================
# AI-Powered Question Generation (Module 3)
# ============================================================
from .ai_service import (
    generate_questions_from_pdf,
    APIKeyMissingError,
    PDFExtractionError,
    AIGenerationError,
)
from .forms import AIQuestionGenerationForm


@login_required
@teacher_required
def ai_generate_form_view(request, exam_id):
    """Show the AI generation form (PDF upload + parameters)."""
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)

    if request.method == 'POST':
        form = AIQuestionGenerationForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = form.cleaned_data['pdf_file']
            num_questions = form.cleaned_data['num_questions']
            total_marks = form.cleaned_data['total_marks']

            try:
                # Call AI service
                questions = generate_questions_from_pdf(
                    pdf_file, num_questions, total_marks
                )

                # Store in session for preview page
                request.session[f'ai_questions_{exam.id}'] = questions
                return redirect('ai_preview', exam_id=exam.id)

            except APIKeyMissingError:
                messages.error(
                    request,
                    'AI service is not configured. '
                    'Please contact your administrator to set up the API key.'
                )
            except PDFExtractionError as e:
                messages.error(request, f'PDF Error: {str(e)}')
            except AIGenerationError as e:
                messages.error(request, f'AI Generation Error: {str(e)}')
            except Exception as e:
                messages.error(request, f'Unexpected error: {str(e)}')
    else:
        form = AIQuestionGenerationForm()

    return render(request, 'exams/ai_generate_form.html', {
        'form': form,
        'exam': exam,
    })


@login_required
@teacher_required
def ai_preview_view(request, exam_id):
    """Show generated questions for review and editing."""
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    session_key = f'ai_questions_{exam.id}'
    questions = request.session.get(session_key)

    if not questions:
        messages.warning(
            request,
            'No AI-generated questions found. Please generate first.'
        )
        return redirect('ai_generate', exam_id=exam.id)

    return render(request, 'exams/ai_preview.html', {
        'exam': exam,
        'questions': questions,
    })


@login_required
@teacher_required
def ai_save_view(request, exam_id):
    """Save edited AI questions to the database."""
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    session_key = f'ai_questions_{exam.id}'

    if request.method != 'POST':
        return redirect('ai_preview', exam_id=exam.id)

    # Parse the submitted questions from POST data
    submitted_count = int(request.POST.get('question_count', 0))
    saved_count = 0

    for i in range(submitted_count):
        # Skip deleted questions
        if request.POST.get(f'deleted_{i}') == '1':
            continue

        question_text = request.POST.get(f'question_text_{i}', '').strip()
        option_a = request.POST.get(f'option_a_{i}', '').strip()
        option_b = request.POST.get(f'option_b_{i}', '').strip()
        option_c = request.POST.get(f'option_c_{i}', '').strip()
        option_d = request.POST.get(f'option_d_{i}', '').strip()
        correct_option = request.POST.get(f'correct_option_{i}', 'A').strip().upper()
        marks_str = request.POST.get(f'marks_{i}', '1')

        # Skip if any field is empty
        if not all([question_text, option_a, option_b, option_c, option_d]):
            continue

        try:
            marks = float(marks_str)
        except (ValueError, TypeError):
            marks = 1.0

        if correct_option not in ['A', 'B', 'C', 'D']:
            correct_option = 'A'

        Question.objects.create(
            exam=exam,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
            marks=marks,
        )
        saved_count += 1

    # Update exam's total_marks
    exam.total_marks = sum(q.marks for q in exam.questions.all())
    exam.save()

    # Clear session
    if session_key in request.session:
        del request.session[session_key]

    if saved_count > 0:
        messages.success(
            request,
            f'Successfully added {saved_count} AI-generated questions to the exam.'
        )
    else:
        messages.warning(request, 'No questions were saved.')

    return redirect('exam_detail', pk=exam.id)