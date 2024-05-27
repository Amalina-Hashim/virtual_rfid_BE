from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=5, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username

class Location(models.Model):
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)  
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True) 
    address_name = models.CharField(max_length=255, null=True, blank=True)
    location_name = models.CharField(max_length=255)
    radius = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    polygon_points = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.location_name

class Day(models.Model):
    name = models.CharField(max_length=9)

    def __str__(self):
        return self.name

class Month(models.Model):
    name = models.CharField(max_length=9)

    def __str__(self):
        return self.name

class Year(models.Model):
    year = models.IntegerField()

    def __str__(self):
        return str(self.year)

class ChargingLogic(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    amount_to_charge = models.DecimalField(max_digits=10, decimal_places=2)
    amount_rate = models.CharField(max_length=10, choices=[('second', 'Per Second'), ('minute', 'Per Minute'), ('hour', 'Per Hour'), ('day', 'Per Day'), ('week', 'Per Week'), ('month', 'Per Month')])
    days = models.ManyToManyField(Day)
    months = models.ManyToManyField(Month)
    years = models.ManyToManyField(Year)

    def __str__(self):
        return f"{self.location.location_name} - {self.amount_to_charge} {self.amount_rate}"

    def is_applicable(self, date_time):
        return (
            date_time.strftime('%A') in [day.name for day in self.days.all()] and
            date_time.strftime('%B') in [month.name for month in self.months.all()] and
            date_time.year in [year.year for year in self.years.all()]
        )

class TransactionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.user.username} - {self.amount} at {self.location.location_name} on {self.timestamp}"
