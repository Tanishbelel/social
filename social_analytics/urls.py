from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('add-account/', views.add_account, name='add_account'),
    path('analytics/', views.analytics, name='analytics'),
    path('ai-query/', views.ai_query, name='ai_query'),
    path('insights/', views.insights, name='insights'),
    path('best-time/', views.best_time_to_post, name='best_time'),
    path('competitor/', views.competitor_analysis, name='competitor'),
    path('viral-predictor/', views.viral_predictor, name='viral_predictor'),
    path('export-report/', views.export_report, name='export_report'),
]