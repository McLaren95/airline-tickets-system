from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('export/', views.export_page, name='export_page'),
    path('export/flights/csv/', views.export_flights_csv, name='export_flights_csv'),
    path('export/flights/json/', views.export_flights_json, name='export_flights_json'),
    path('export/flights/upcoming/csv/', views.export_upcoming_flights_csv, name='export_upcoming_flights_csv'),
    path('export/flights/upcoming/json/', views.export_upcoming_flights_json, name='export_upcoming_flights_json'),
    path('flights/', views.flight_search, name='flight_search'),
    path('book/<int:flight_id>/', views.book_flight, name='book_flight'),
    path('payment/<str:book_ref>/', views.payment_page, name='payment_page'),
    path('payment/success/<str:book_ref>/', views.payment_success, name='payment_success'),
]