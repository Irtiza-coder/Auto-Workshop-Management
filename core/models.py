from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers', null=True, blank=True)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class Vehicle(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50) # e.g., Honda
    model = models.CharField(max_length=50) # e.g., Civic
    number_plate = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.make} {self.model} - {self.number_plate}"


class Part(models.Model):
    CATEGORY_CHOICES = [
        ('Genuine',     'Genuine'),
        ('OEM',         'OEM'),
        ('Aftermarket', 'Aftermarket'),
        ('Used',        'Used'),
        ('Local',       'Local'),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parts', null=True, blank=True)
    name         = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100, blank=True, default='', help_text="Brand/manufacturer e.g. Toyota, Bosch")
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Genuine')
    quantity     = models.PositiveIntegerField(default=0)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Original cost from supplier")
    price        = models.DecimalField(max_digits=10, decimal_places=2, help_text="Your selling price to customer")

    @property
    def profit_per_unit(self):
        return self.price - self.buying_price

    @property
    def profit_margin_percent(self):
        if self.buying_price > 0:
            return ((self.price - self.buying_price) / self.buying_price) * 100
        return 0

    @property
    def is_low_stock(self):
        return self.quantity < 5

    def __str__(self):
        return self.name


class Service(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services', null=True, blank=True)
    name          = models.CharField(max_length=150)
    default_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Default price/labour cost in Rs.")
    description   = models.TextField(blank=True, default='', help_text="Optional description of service")
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — Rs.{self.default_price}"



class JobCard(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    user                = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_cards', null=True, blank=True)
    customer            = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='job_cards')
    vehicle             = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='job_cards')
    problem_description = models.TextField()
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    # labor_cost kept for backward-compatibility; new labour items stored in JobLabour
    labor_cost          = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    mileage             = models.CharField(max_length=30, blank=True, default='', help_text="Optional vehicle mileage at time of service")
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job #{self.id} - {self.vehicle.number_plate} ({self.status})"

    def calculate_total_cost(self):
        parts_cost  = sum(job_part.get_cost() for job_part in self.job_parts.all())
        labour_cost = sum(jl.cost for jl in self.job_labours.all())
        return parts_cost + labour_cost

    def total_parts_cost(self):
        return sum(job_part.get_cost() for job_part in self.job_parts.all())

    def total_labour_cost(self):
        return sum(jl.cost for jl in self.job_labours.all())

    @property
    def payment_status(self):
        if hasattr(self, 'invoice') and self.invoice:
            return self.invoice.payment_status
        return 'Unpaid'


class JobLabour(models.Model):
    """Individual labour line items on a job card (replaces single labor_cost field)."""
    job_card    = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='job_labours')
    description = models.CharField(max_length=200, help_text="e.g. Self Motor Labour, Oil Change Labour")
    cost        = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} — Rs.{self.cost} (Job #{self.job_card.id})"


class JobPart(models.Model):
    job_card       = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='job_parts')
    part           = models.ForeignKey(Part, on_delete=models.PROTECT)
    quantity       = models.PositiveIntegerField(default=1)
    price_at_time  = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of part at the time of job")

    def save(self, *args, **kwargs):
        if not self.price_at_time:
            self.price_at_time = self.part.price
        super().save(*args, **kwargs)

    def get_cost(self):
        return self.quantity * self.price_at_time

    def __str__(self):
        return f"{self.quantity}x {self.part.name} for Job #{self.job_card.id}"


class Invoice(models.Model):
    PAYMENT_CHOICES = [
        ('Unpaid',  'Unpaid'),
        ('Partial', 'Partial'),
        ('Paid',    'Paid'),
    ]

    job_card       = models.OneToOneField(JobCard, on_delete=models.CASCADE, related_name='invoice')
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid    = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='Unpaid')
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def balance_due(self):
        return max(self.total_amount - self.amount_paid, Decimal('0.00')) if hasattr(self, 'total_amount') else 0

    @property
    def is_fully_paid(self):
        return self.payment_status == 'Paid' or self.amount_paid >= self.total_amount

    def __str__(self):
        return f"Invoice #{self.id} for Job #{self.job_card.id} ({self.payment_status})"
