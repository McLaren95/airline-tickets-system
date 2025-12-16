from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db import transaction
from django.db import models
from datetime import timedelta
from django.db.models import Q
import csv
import json
from django.http import HttpResponse, JsonResponse
from .models import Flight, Booking, Ticket, Segment, Airport, Payment, Seat, BoardingPass
import re
import uuid
import random
import string

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
    if request.user.is_staff or request.user.groups.filter(name='Managers').exists():
        return redirect('/admin/')
    return render(request, 'profile.html')

def is_manager_or_staff(user):
    return user.is_staff or user.groups.filter(name='Managers').exists()

@login_required
@user_passes_test(is_manager_or_staff)
def export_page(request):
    return render(request, 'export.html')

@login_required
@user_passes_test(is_manager_or_staff)
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

@login_required
@user_passes_test(is_manager_or_staff)
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

@login_required
@user_passes_test(is_manager_or_staff)
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

@login_required
@user_passes_test(is_manager_or_staff)
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
    ).filter(scheduled_departure__gte=timezone.now())

    departure_query = request.GET.get('departure', '').strip()
    arrival_query = request.GET.get('arrival', '').strip()
    date_str = request.GET.get('date')

    def extract_code(query):
        match = re.search(r'\(([A-Z0-9]{3})\)$', query)
        if match:
            return match.group(1)
        return query

    if departure_query:
        clean_dep = extract_code(departure_query)
        flights = flights.filter(
            Q(route__departure_airport__airport_code__icontains=clean_dep) |
            Q(route__departure_airport__city__icontains=clean_dep)
        )

    if arrival_query:
        clean_arr = extract_code(arrival_query)
        flights = flights.filter(
            Q(route__arrival_airport__airport_code__icontains=clean_arr) |
            Q(route__arrival_airport__city__icontains=clean_arr)
        )

    if date_str:
        try:
            # Тут фильтруем конкретно по дню
            flights = flights.filter(scheduled_departure__date=date_str)
        except ValueError:
            pass

    flights = flights.order_by('scheduled_departure')

    return render(request, 'flight_search.html', {'flights': flights})


@login_required
def book_flight(request, flight_id):
    flight = get_object_or_404(Flight, pk=flight_id)
    base_price = 5500

    if request.method == 'POST':
        try:
            with transaction.atomic():
                passenger_name = request.POST.get('passenger_name')
                passenger_id = request.POST.get('passenger_id')
                fare_conditions = request.POST.get('fare_conditions')

                price = base_price
                if fare_conditions == 'Business':
                    price *= 3
                elif fare_conditions == 'Comfort':
                    price *= 1.5

                book_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                booking = Booking.objects.create(
                    book_ref=book_ref,
                    book_date=timezone.now(),
                    total_amount=price,
                    user=request.user,
                    is_paid=False
                )

                ticket_no = ''.join(random.choices(string.digits, k=13))
                ticket = Ticket.objects.create(
                    ticket_no=ticket_no,
                    booking=booking,
                    passenger_id=passenger_id,
                    passenger_name=passenger_name,
                    outbound=True
                )

                Segment.objects.create(
                    ticket=ticket,
                    flight=flight,
                    fare_conditions=fare_conditions,
                    price=price
                )

                airplane = flight.route.airplane
                available_seats = Seat.objects.filter(
                    airplane=airplane,
                    fare_conditions=fare_conditions
                )

                if available_seats.exists():
                    assigned_seat = random.choice(available_seats)

                    b_time = flight.scheduled_departure - timedelta(minutes=40)

                    BoardingPass.objects.create(
                        ticket=ticket,
                        flight=flight,
                        seat=assigned_seat,
                        boarding_no=random.randint(1, 200),
                        boarding_time=b_time
                    )

                return redirect('payment_page', book_ref=book_ref)

        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, "Ошибка при бронировании.")

    return render(request, 'book_flight.html', {'flight': flight, 'base_price': base_price})

def payment_page(request, book_ref):
    booking = get_object_or_404(Booking, book_ref=book_ref, user=request.user)
    return render(request, 'payment.html', {'booking': booking})


def payment_success(request, book_ref):
    booking = get_object_or_404(Booking, book_ref=book_ref)

    if not booking.is_paid:
        booking.is_paid = True
        booking.save()

        transaction_id = str(uuid.uuid4()).replace('-', '')[:16].upper()

        Payment.objects.create(
            payment_id=transaction_id,
            booking=booking,
            amount=booking.total_amount,
            payment_method='Bank Card (Test)'
        )

        messages.success(request, f'Оплата прошла успешно! Транзакция №{transaction_id}')
    else:
        messages.info(request, 'Этот заказ уже был оплачен ранее.')

    return redirect('profile')

def airport_autocomplete(request):
    term = request.GET.get('term', '').lower()
    if len(term) < 2:
        return JsonResponse([], safe=False)

    airports = Airport.objects.filter(
        models.Q(airport_code__icontains=term) |
        models.Q(city__icontains=term)
    )[:10]

    results = []
    for airport in airports:
        city_name = airport.city.get('ru', airport.city.get('en', ''))
        results.append({
            'label': f"{city_name} ({airport.airport_code})",
            'value': airport.airport_code
        })

    return JsonResponse(results, safe=False)

