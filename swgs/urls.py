from django.contrib.auth import views as auth_view
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_swgs, name="home_swgs"),
    path('view_runs/', views.view_runs, name="view_runs"),
    path('view_patient_analysis/<str:patient_id>', views.view_patient_analysis, name="view_patient_analysis"),
    path('view_panels/', views.view_panels, name="view_panels"),
    path('view_panel/<str:panel_id>', views.view_panel, name="view_panel")
]