from django.contrib import admin
from .models import Airplane, Airport, Seat

admin.site.register(Airplane)
admin.site.register(Airport)
admin.site.register(Seat)