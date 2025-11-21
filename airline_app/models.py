from django.db import models
from django.contrib.postgres.fields import ArrayField

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