from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import DateTimeRangeField
from django.core.exceptions import ValidationError


class Airplane(models.Model):
    airplane_code = models.CharField(max_length=3, primary_key=True)
    model = models.JSONField()
    range = models.PositiveIntegerField()
    speed = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.airplane_code} ({self.model.get('en', '')})"

    class Meta:
        db_table = 'airplanes_data'

class Airport(models.Model):
    airport_code = models.CharField(max_length=3, primary_key=True)
    airport_name = models.JSONField()
    city = models.JSONField()
    country = models.JSONField()
    longitude = models.FloatField()
    latitude = models.FloatField()
    timezone = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.airport_code} ({self.airport_name.get('en', '')})"

    class Meta:
        db_table = 'airports_data'

class Seat(models.Model):
    FARE_CONDITIONS = [
        ('Economy', 'Economy'),
        ('Comfort', 'Comfort'),
        ('Business', 'Business'),
    ]

    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE)
    seat_no = models.CharField(max_length=10)
    fare_conditions = models.CharField(max_length=20, choices=FARE_CONDITIONS)

    class Meta:
        db_table = 'seats'
        unique_together = (('airplane', 'seat_no'),)

    def __str__(self):
        return f"{self.seat_no} ({self.fare_conditions})"

class Booking(models.Model):
    book_ref = models.CharField(max_length=6, primary_key=True)
    book_date = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'bookings'

    def __str__(self):
        return self.book_ref

class Ticket(models.Model):
    ticket_no = models.CharField(max_length=16, primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    passenger_id = models.CharField(max_length=64)
    passenger_name = models.CharField(max_length=255)
    outbound = models.BooleanField()

    class Meta:
        db_table = 'tickets'

    def __str__(self):
        return f"{self.ticket_no} - {self.passenger_name}"

class Route(models.Model):
    route_no = models.CharField(max_length=64, primary_key=True)
    validity = DateTimeRangeField()
    departure_airport = models.ForeignKey(
        Airport, on_delete=models.CASCADE,
        related_name='departing_routes'
    )
    arrival_airport = models.ForeignKey(
        Airport, on_delete=models.CASCADE,
        related_name='arriving_routes'
    )
    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE)
    days_of_week = ArrayField(models.IntegerField())
    scheduled_time = models.TimeField()
    duration = models.DurationField()

    class Meta:
        db_table = 'routes'

    def __str__(self):
        return f"{self.route_no}: {self.departure_airport} → {self.arrival_airport}"

class Flight(models.Model):
    SCHEDULED = 'Scheduled'
    ON_TIME = 'On Time'
    DELAYED = 'Delayed'
    BOARDING = 'Boarding'
    DEPARTED = 'Departed'
    ARRIVED = 'Arrived'
    CANCELLED = 'Cancelled'

    STATUS_CHOICES = [
        (SCHEDULED, 'Scheduled'),
        (ON_TIME, 'On Time'),
        (DELAYED, 'Delayed'),
        (BOARDING, 'Boarding'),
        (DEPARTED, 'Departed'),
        (ARRIVED, 'Arrived'),
        (CANCELLED, 'Cancelled'),
    ]

    flight_id = models.AutoField(primary_key=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, db_column='route_no', to_field='route_no')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    scheduled_departure = models.DateTimeField()
    scheduled_arrival = models.DateTimeField()
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.route.route_no} - {self.scheduled_departure.date()}"

    def clean(self):
        if self.scheduled_arrival <= self.scheduled_departure:
            raise ValidationError("Scheduled arrival must be after departure.")
        if self.actual_arrival and (
            not self.actual_departure or
            self.actual_arrival <= self.actual_departure
        ):
            raise ValidationError("Actual arrival must be after actual departure.")

    class Meta:
        db_table = 'flights'