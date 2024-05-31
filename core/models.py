import logging
from django.db import models
from django.contrib.auth.models import AbstractUser

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    first_login = models.BooleanField(default=True)  
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
    is_enabled = models.BooleanField(default=True)

    def is_applicable(self, date_time):
        if not self.is_enabled:
            return False
        return (
            date_time.strftime('%A').lower() in [day.name.lower() for day in self.days.all()] and
            date_time.strftime('%B').lower() in [month.name.lower() for month in self.months.all()] and
            date_time.year in [year.year for year in self.years.all()] and
            self.start_time <= date_time.time() <= self.end_time
        )

class TransactionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_rate = models.CharField(
        max_length=10,
        choices=[
            ('second', 'Per Second'),
            ('minute', 'Per Minute'),
            ('hour', 'Per Hour'),
            ('day', 'Per Day'),
            ('week', 'Per Week'),
            ('month', 'Per Month')
        ],
        default='hour' 
    )

    def __str__(self):
        return f"{self.user.username} - {self.amount} at {self.location.location_name} on {self.timestamp} at rate {self.amount_rate}"

    def save(self, *args, **kwargs):
        original_balance = self.user.balance
        self.user.balance -= self.amount
        logger.debug(f"Original balance: {original_balance}, amount: {self.amount}, new balance: {self.user.balance}")
        self.user.save()
        super(TransactionHistory, self).save(*args, **kwargs)

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} on {self.timestamp}"