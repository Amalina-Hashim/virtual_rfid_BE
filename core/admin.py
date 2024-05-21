from django.contrib import admin
from .models import Day, Month, Year, Location, ChargingLogic, User, TransactionHistory

admin.site.register(Day)
admin.site.register(Month)
admin.site.register(Year)
admin.site.register(Location)
admin.site.register(ChargingLogic)
admin.site.register(User)
admin.site.register(TransactionHistory)


