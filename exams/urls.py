from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('create/', views.exam_create, name='exam_create'),
    path('books/', views.books_page, name='books_page'),
    path('pyq/', views.pyq_page, name='pyq_page'),
    path('support/', views.support_page, name='support_page'),
    path('<int:pk>/', views.exam_detail, name='exam_detail'),
    path('<int:pk>/edit/', views.exam_update, name='exam_update'),
    path('<int:pk>/delete/', views.exam_delete, name='exam_delete'),
    path('<int:exam_id>/questions/add/', views.question_create, name='question_create'),
    path('questions/<int:pk>/edit/', views.question_update, name='question_update'),
    path('questions/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('<int:exam_id>/instructions/', views.exam_instructions, name='exam_instructions'),
    path('<int:exam_id>/take/', views.take_exam, name='take_exam'),
    path('results/', views.result_list, name='result_list'),
    path('results/<int:pk>/pdf/', views.result_pdf, name='result_pdf'),
    path('results/<int:pk>/', views.result_detail, name='result_detail'),

    # AI Question Generation (Module 3)
    path('<int:exam_id>/ai-generate/', views.ai_generate_form_view, name='ai_generate'),
    path('<int:exam_id>/ai-preview/', views.ai_preview_view, name='ai_preview'),
    path('<int:exam_id>/ai-save/', views.ai_save_view, name='ai_save'),
]