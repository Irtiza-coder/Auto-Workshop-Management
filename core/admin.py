from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.core import serializers
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Customer, Vehicle, Part, Service, JobCard, JobLabour, JobPart, Invoice

def export_full_database_backup(request):
    """Admin-only view to export all database models into a JSON backup file."""
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=401)
    
    models_to_export = [
        User, Customer, Vehicle, Part, Service, JobCard, JobLabour, JobPart, Invoice
    ]
    all_objects = []
    for model in models_to_export:
        all_objects.extend(model.objects.all())
        
    data = serializers.serialize("json", all_objects, indent=2)
    response = HttpResponse(data, content_type='application/json')
    filename = f"autoshop_full_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# Extend Django Admin URLs
original_get_urls = admin.site.get_urls
def get_urls():
    custom_urls = [
        path('export-database-backup/', admin.site.admin_view(export_full_database_backup), name='export_database_backup'),
    ]
    return custom_urls + original_get_urls()

admin.site.get_urls = get_urls
admin.site.site_header = "AutoShop Pro Admin"
admin.site.site_title = "AutoShop Pro Admin Portal"
admin.site.index_title = "System Management & Database Administration"


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
    list_display = ('name', 'quantity', 'buying_price', 'price', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'company_name')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_price', 'created_at')
    search_fields = ('name',)

class JobPartInline(admin.TabularInline):
    model = JobPart
    extra = 1

class JobLabourInline(admin.TabularInline):
    model = JobLabour
    extra = 1

@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'customer', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('vehicle__number_plate', 'customer__name')
    inlines = [JobLabourInline, JobPartInline]

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_card', 'total_amount', 'amount_paid', 'payment_status', 'created_at')
    list_filter = ('payment_status',)
