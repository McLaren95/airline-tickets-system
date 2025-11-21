from django.db import models
from django.contrib.postgres.fields import ArrayField

class Airplane(models.Model):
    airplane_code = models.CharField(max_length=10, primary_key=True)
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
