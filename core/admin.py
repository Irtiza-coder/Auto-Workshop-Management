from django.contrib import admin
from .models import Customer, Vehicle, Part, JobCard, JobPart, Invoice

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'created_at')
    search_fields = ('name', 'phone_number')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('number_plate', 'make', 'model', 'customer')
    list_filter = ('make',)
    search_fields = ('number_plate', 'customer__name')

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'price')
    search_fields = ('name',)

class JobPartInline(admin.TabularInline):
    model = JobPart
    extra = 1

@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'customer', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('vehicle__number_plate', 'customer__name')
    inlines = [JobPartInline]

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_card', 'total_amount', 'created_at')
