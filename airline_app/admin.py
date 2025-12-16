from django.contrib import admin
from .models import Airplane, Airport, Seat, Booking, Ticket, Route, Flight, Segment, BoardingPass, Payment

admin.site.register(Airplane)
admin.site.register(Airport)
admin.site.register(Seat)
admin.site.register(Booking)
admin.site.register(Ticket)
admin.site.register(Route)
admin.site.register(Flight)
admin.site.register(Segment)
admin.site.register(BoardingPass)
admin.site.register(Payment)