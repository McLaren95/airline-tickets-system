from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django.utils import timezone
import csv
import json
from django.http import HttpResponse, JsonResponse
from .models import Flight, Booking, Ticket, Segment
from django.db import models

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


def flight_search(request):
    flights = Flight.objects.select_related(
        'route__departure_airport',
        'route__arrival_airport',
        'route__airplane'
    ).all()

    departure_query = request.GET.get('departure', '').strip().lower()
    arrival_query = request.GET.get('arrival', '').strip().lower()
    date_str = request.GET.get('date')

    if departure_query:
        flights = flights.filter(
            models.Q(route__departure_airport__airport_code__icontains=departure_query.upper()) |
            models.Q(route__departure_airport__city__icontains=departure_query.capitalize()) |
            models.Q(route__departure_airport__city__icontains=departure_query)
        )

    if arrival_query:
        flights = flights.filter(
            models.Q(route__arrival_airport__airport_code__icontains=arrival_query.upper()) |
            models.Q(route__arrival_airport__city__icontains=arrival_query.capitalize()) |
            models.Q(route__arrival_airport__city__icontains=arrival_query)
        )

    if date_str:
        try:
            from datetime import datetime
            search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            flights = flights.filter(scheduled_departure__date=search_date)
        except ValueError:
            pass

    flights = flights.order_by('scheduled_departure')

    return render(request, 'flight_search.html', {'flights': flights})


@login_required
def book_flight(request, flight_id):
    flight = get_object_or_404(Flight, pk=flight_id)

    base_price = 5500

    if request.method == 'POST':
        import random
        import string

        book_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        passenger_name = request.POST.get('passenger_name')
        passenger_id = request.POST.get('passenger_id')
        fare_conditions = request.POST.get('fare_conditions')
        seat_selected = request.POST.get('seat')

        total_amount = base_price
        if fare_conditions == 'Business':
            total_amount *= 3
        elif fare_conditions == 'Comfort':
            total_amount *= 1.5

        booking = Booking.objects.create(
            book_ref=book_ref,
            book_date=timezone.now(),
            total_amount=total_amount,
            user=request.user
        )

        ticket_no = ''.join(random.choices(string.digits, k=13))
        Ticket.objects.create(
            ticket_no=ticket_no,
            booking=booking,
            passenger_id=passenger_id,
            passenger_name=passenger_name,
            outbound=True  # или логика туда-обратно
        )

        return redirect('payment_page', book_ref=book_ref)

    context = {
        'flight': flight,
        'base_price': base_price,
    }
    return render(request, 'book_flight.html', context)

def payment_page(request, book_ref):
    booking = get_object_or_404(Booking, book_ref=book_ref, user=request.user)
    return render(request, 'payment.html', {'booking': booking})

def payment_success(request, book_ref):
    booking = get_object_or_404(Booking, book_ref=book_ref)
    messages.success(request, f'Бронирование {book_ref} успешно оплачено!')
    return redirect('profile')