from django.urls import path

from . import views

urlpatterns = [
    path("", views.Accueil.as_view(), name="home"),
    path("cadeaux/<int:pk>/interet/", views.declare_interest, name="interet"),
    path("cadeaux/<int:pk>/pas-interesse/", views.declare_not_interested, name="not_interet"),
    path("cadeaux/<int:pk>/achete/", views.declare_bought, name="bought"),
    path("cadeaux/<int:pk>/pas-achete/", views.declare_not_bought, name="not_bought"),
    path("register/", views.register_request, name="register"),
]
