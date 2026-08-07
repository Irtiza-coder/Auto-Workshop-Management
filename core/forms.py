from django import forms
from .models import JobCard, Customer, Vehicle

class BookAppointmentForm(forms.ModelForm):
    customer_name = forms.CharField(max_length=100)
    customer_phone = forms.CharField(max_length=20)
    vehicle_make = forms.CharField(max_length=50)
    vehicle_model = forms.CharField(max_length=50)
    vehicle_plate = forms.CharField(max_length=20)

    class Meta:
        model = JobCard
        fields = ['problem_description']

    def save(self, commit=True):
        # 1. Get or create Customer
        customer, _ = Customer.objects.get_or_create(
            phone_number=self.cleaned_data['customer_phone'],
            defaults={'name': self.cleaned_data['customer_name']}
        )
        
        # 2. Get or create Vehicle
        vehicle, _ = Vehicle.objects.get_or_create(
            number_plate=self.cleaned_data['vehicle_plate'],
            defaults={
                'customer': customer,
                'make': self.cleaned_data['vehicle_make'],
                'model': self.cleaned_data['vehicle_model']
            }
        )

        # 3. Create Job Card
        job_card = super().save(commit=False)
        job_card.customer = customer
        job_card.vehicle = vehicle
        if commit:
            job_card.save()
        return job_card
