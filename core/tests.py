from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Customer, Vehicle, Part, JobCard, JobPart, JobLabour, Invoice


class WorkshopModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="John Doe", phone_number="03001234567")
        self.vehicle  = Vehicle.objects.create(customer=self.customer, make="Toyota", model="Corolla", number_plate="ABC-123")
        self.part     = Part.objects.create(
            name="Engine Oil 4L",
            company_name="Shell",
            category="Genuine",
            quantity=3,
            buying_price=Decimal("3000.00"),
            price=Decimal("4500.00")
        )

    def test_part_properties(self):
        self.assertEqual(self.part.profit_per_unit, Decimal("1500.00"))
        self.assertAlmostEqual(self.part.profit_margin_percent, 50.0)
        self.assertTrue(self.part.is_low_stock)

    def test_jobcard_total_calculation_with_multiple_labour(self):
        job = JobCard.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            problem_description="Oil Change & Filter"
        )
        JobPart.objects.create(job_card=job, part=self.part, quantity=2, price_at_time=self.part.price)
        JobLabour.objects.create(job_card=job, description="Oil Change Labour", cost=Decimal("500.00"))
        JobLabour.objects.create(job_card=job, description="Filter Fitting Labour", cost=Decimal("500.00"))

        # 2 * 4500 (parts) = 9000; 500 + 500 (labour) = 1000; total = 10000
        self.assertEqual(job.total_parts_cost(), Decimal("9000.00"))
        self.assertEqual(job.total_labour_cost(), Decimal("1000.00"))
        self.assertEqual(job.calculate_total_cost(), Decimal("10000.00"))

    def test_invoice_payment_balance(self):
        job = JobCard.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            problem_description="Brake Pad Replacement",
            status="Completed"
        )
        JobLabour.objects.create(job_card=job, description="Brake Fitting", cost=Decimal("2000.00"))
        invoice = Invoice.objects.create(
            job_card=job,
            total_amount=Decimal("5000.00"),
            amount_paid=Decimal("2000.00"),
            payment_status="Partial"
        )

        self.assertEqual(invoice.balance_due, Decimal("3000.00"))
        self.assertFalse(invoice.is_fully_paid)
        self.assertEqual(job.payment_status, "Partial")

        invoice.amount_paid = Decimal("5000.00")
        invoice.payment_status = "Paid"
        invoice.save()
        self.assertEqual(invoice.balance_due, Decimal("0.00"))
        self.assertTrue(invoice.is_fully_paid)
        self.assertEqual(job.payment_status, "Paid")


class WorkshopViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="password123")
        self.client = Client()
        self.client.login(username="admin", password="password123")

        self.customer = Customer.objects.create(user=self.user, name="Jane Smith", phone_number="03009876543")
        self.vehicle  = Vehicle.objects.create(customer=self.customer, make="Honda", model="Civic", number_plate="XYZ-789")
        self.part     = Part.objects.create(
            user=self.user,
            name="Brake Pad Front",
            company_name="Bosch",
            category="OEM",
            quantity=10,
            buying_price=Decimal("2000.00"),
            price=Decimal("3500.00")
        )
        self.job = JobCard.objects.create(
            user=self.user,
            customer=self.customer,
            vehicle=self.vehicle,
            problem_description="Squeaking Brakes",
            status="Pending"
        )

    def test_dashboard_accessible(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_customer_list_search(self):
        response = self.client.get(reverse('customer_list') + '?q=Jane')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane Smith")

    def test_customer_detail_profile_view(self):
        response = self.client.get(reverse('customer_detail', args=[self.customer.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jane Smith")
        self.assertContains(response, "Job Cards History")
        self.assertContains(response, "Squeaking Brakes")


    def test_inventory_csv_export(self):
        response = self.client.get(reverse('export_inventory_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="inventory_export.csv"', response['Content-Disposition'])
        self.assertContains(response, "Brake Pad Front")

    def test_jobcard_print_view(self):
        response = self.client.get(reverse('jobcard_print', args=[self.job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "JOB RECEIPT")
        self.assertContains(response, "XYZ-789")

    def test_add_and_remove_labour_action(self):
        # Test adding labour via POST
        response = self.client.post(reverse('jobcard_detail', args=[self.job.id]), {
            'action': 'add_labour',
            'labour_description': 'Self Labour',
            'labour_cost': '500.00'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobLabour.objects.filter(job_card=self.job).count(), 1)
        labour = JobLabour.objects.get(job_card=self.job)
        self.assertEqual(labour.description, 'Self Labour')
        self.assertEqual(labour.cost, Decimal('500.00'))

        # Test removing labour
        response = self.client.post(reverse('jobcard_detail', args=[self.job.id]), {
            'action': 'remove_labour',
            'labour_id': labour.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobLabour.objects.filter(job_card=self.job).count(), 0)

    def test_service_catalog(self):
        # Test adding a service to catalog
        response = self.client.post(reverse('service_list'), {
            'action': 'add_service',
            'name': 'Full Engine Tuning',
            'default_price': '3500.00',
            'description': 'Full tuning test'
        })
        self.assertEqual(response.status_code, 302)

        from core.models import Service
        self.assertTrue(Service.objects.filter(name='Full Engine Tuning').exists())

        # Test viewing services list page
        response = self.client.get(reverse('service_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full Engine Tuning')

