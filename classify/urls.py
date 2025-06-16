from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("<str:query>", views.view_classifications, name="view-classifications"),
    path("classify/<str:classification>", views.classify, name="perform-classification"),
    path("ajax/submit_classification_selections/", views.ajax_classify, name="ajax-classification"),
]
