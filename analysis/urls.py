from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='analysis/sign-in.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='analysis/sign-in.html'), name='logout'),

    path('options/', views.options_page, name='options_page'),
    path('options/settings', views.user_settings, name='user_settings'),
    path('change_password/', views.change_password, name='change_password'),

    path('view_worksheets/<str:query>', views.view_worksheets, name='view_worksheets'),
    path('worksheets/<str:worksheet_id>', views.view_samples, name='view_samples'),
    path('analysis/<str:sample_id>', views.analysis_sheet, name='analysis_sheet'),
    path('ajax/submit_variant_selections/', views.ajax, name='ajax'),

    path('variant_lists/polys/<str:list_name>', views.view_polys, name='view_polys'),
    path('variant_lists/artefacts/<str:list_name>', views.view_artefacts, name='view_artefacts'),
]
