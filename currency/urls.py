from django.urls import path
from . import views

urlpatterns = [
    path("rates/latest/", views.latest_exchange_rates, name="latest_exchange_rates"),
    path("rates/<str:currency>/history/", views.currency_history, name="currency_history"),
    path("rates/<str:currency>/latest/", views.currency_latest, name="currency_latest"),
    path("rates/sources/", views.sources_list, name="sources_list"),
]