from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import Group
import csv
import json
from django.http import HttpResponse, JsonResponse
from .models import Flight

def custom_logout(request):
    logout(request)
    return redirect('home')

def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            clients_group = Group.objects.get(name='Clients')
            user.groups.add(clients_group)
            messages.success(request, 'Регистрация успешна!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'profile.html')

def export_page(request):
    return render(request, 'export.html')

def export_flights_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="flights.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID рейса', 'Номер маршрута', 'Аэропорт вылета', 'Аэропорт прилета',
                     'Плановый вылет', 'Плановый прилет', 'Статус'])

    flights = Flight.objects.select_related('route__departure_airport', 'route__arrival_airport').all()

    for flight in flights:
        writer.writerow([
            flight.flight_id,
            flight.route.route_no,
            flight.route.departure_airport.airport_code,
            flight.route.arrival_airport.airport_code,
            flight.scheduled_departure.strftime('%Y-%m-%d %H:%M'),
            flight.scheduled_arrival.strftime('%Y-%m-%d %H:%M'),
            flight.get_status_display()
        ])

    return response

def export_flights_json(request):
    flights = Flight.objects.select_related('route__departure_airport', 'route__arrival_airport').all()

    data = []
    for flight in flights:
        data.append({
            'flight_id': flight.flight_id,
            'route_no': flight.route.route_no,
            'departure_airport': flight.route.departure_airport.airport_code,
            'arrival_airport': flight.route.arrival_airport.airport_code,
            'scheduled_departure': flight.scheduled_departure.strftime('%Y-%m-%d %H:%M'),
            'scheduled_arrival': flight.scheduled_arrival.strftime('%Y-%m-%d %H:%M'),
            'status': flight.get_status_display(),
            'status_code': flight.status
        })

    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False, 'indent': 2})


def export_upcoming_flights_csv(request):
    from datetime import date, timedelta

    today = date.today()
    seven_days_later = today + timedelta(days=7)

    flights = Flight.objects.filter(
        scheduled_departure__date__range=[today, seven_days_later]
    ).select_related('route__departure_airport', 'route__arrival_airport')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="upcoming_flights_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID рейса', 'Маршрут', 'Откуда', 'Куда',
                     'Вылет', 'Прилет', 'Статус', 'Дней до вылета'])

    for flight in flights:
        days_until = (flight.scheduled_departure.date() - today).days
        writer.writerow([
            flight.flight_id,
            flight.route.route_no,
            flight.route.departure_airport.airport_code,
            flight.route.arrival_airport.airport_code,
            flight.scheduled_departure.strftime('%Y-%m-%d %H:%M'),
            flight.scheduled_arrival.strftime('%Y-%m-%d %H:%M'),
            flight.get_status_display(),
            days_until
        ])

    return response


def export_upcoming_flights_json(request):
    from datetime import date, timedelta

    today = date.today()
    seven_days_later = today + timedelta(days=7)

    flights = Flight.objects.filter(
        scheduled_departure__date__range=[today, seven_days_later]
    ).select_related('route__departure_airport', 'route__arrival_airport')

    data = []
    for flight in flights:
        days_until = (flight.scheduled_departure.date() - today).days
        data.append({
            'flight_id': flight.flight_id,
            'route_no': flight.route.route_no,
            'departure_airport': flight.route.departure_airport.airport_code,
            'arrival_airport': flight.route.arrival_airport.airport_code,
            'scheduled_departure': flight.scheduled_departure.strftime('%Y-%m-%d %H:%M'),
            'scheduled_arrival': flight.scheduled_arrival.strftime('%Y-%m-%d %H:%M'),
            'status': flight.get_status_display(),
            'days_until_departure': days_until,
            'is_upcoming': True if days_until <= 7 else False
        })

    return JsonResponse({
        'generated_date': str(today),
        'date_range': f'{today} - {seven_days_later}',
        'total_flights': len(data),
        'flights': data
    }, safe=False, json_dumps_params={'ensure_ascii': False, 'indent': 2})
