import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workshop_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Customer, Vehicle, Part, Service, JobCard, JobLabour, JobPart, Invoice

User = get_user_model()

def seed():
    # 1. Get or Create user 'Irtiza'
    irtiza, created = User.objects.get_or_create(username='Irtiza', defaults={'email': 'irtiza@workshop.com'})
    if created or not irtiza.has_usable_password():
        irtiza.set_password('user123')
        irtiza.save()

    print(f"Seeding dummy data for user: {irtiza.username}")

    # 2. Customers
    customers_data = [
        {"name": "Muhammad Ali", "phone_number": "0300-1234567"},
        {"name": "Sarah Jenkins", "phone_number": "0321-9876543"},
        {"name": "David Miller", "phone_number": "0312-4567890"},
        {"name": "Ahmed Raza", "phone_number": "0333-5551212"},
        {"name": "Emily Watson", "phone_number": "0345-6789012"},
    ]

    customers = []
    for c_data in customers_data:
        c, _ = Customer.objects.get_or_create(
            user=irtiza,
            phone_number=c_data["phone_number"],
            defaults={"name": c_data["name"]}
        )
        customers.append(c)
    print(f"Seeded {len(customers)} customers.")

    # 3. Vehicles
    vehicles_data = [
        {"customer": customers[0], "make": "Toyota", "model": "Corolla Altis", "number_plate": "LEC-19-2041"},
        {"customer": customers[1], "make": "Honda", "model": "Civic Turbo", "number_plate": "ICT-22-8840"},
        {"customer": customers[2], "make": "Suzuki", "model": "Swift VXL", "number_plate": "LHR-20-4102"},
        {"customer": customers[3], "make": "Hyundai", "model": "Tucson AWD", "number_plate": "KHI-23-9901"},
        {"customer": customers[4], "make": "Kia", "model": "Sportage FW", "number_plate": "ISB-21-3319"},
    ]

    vehicles = []
    for v_data in vehicles_data:
        v, _ = Vehicle.objects.get_or_create(
            number_plate=v_data["number_plate"],
            defaults={
                "customer": v_data["customer"],
                "make": v_data["make"],
                "model": v_data["model"]
            }
        )
        vehicles.append(v)
    print(f"Seeded {len(vehicles)} vehicles.")

    # 4. Parts (Inventory)
    parts_data = [
        {"name": "Synthetic Engine Oil 5W-30", "company_name": "Shell Helix", "category": "Genuine", "quantity": 30, "buying_price": 4500, "price": 6000},
        {"name": "Front Ceramic Brake Pads", "company_name": "Bosch", "category": "OEM", "quantity": 12, "buying_price": 3000, "price": 4500},
        {"name": "Air Filter Element", "company_name": "Toyota Genuine", "category": "Genuine", "quantity": 25, "buying_price": 1200, "price": 1800},
        {"name": "Iridium Spark Plugs Set", "company_name": "NGK", "category": "Aftermarket", "quantity": 15, "buying_price": 2500, "price": 3800},
        {"name": "Oil Filter Cartridge", "company_name": "Denso", "category": "Genuine", "quantity": 40, "buying_price": 600, "price": 1000},
        {"name": "Transmission Fluid ATF", "company_name": "Mobil 1", "category": "OEM", "quantity": 18, "buying_price": 3500, "price": 5000},
    ]

    parts = []
    for p_data in parts_data:
        p, _ = Part.objects.get_or_create(
            user=irtiza,
            name=p_data["name"],
            defaults=p_data
        )
        parts.append(p)
    print(f"Seeded {len(parts)} inventory parts.")

    # 5. Services
    services_data = [
        {"name": "Full Periodic Maintenance Service", "default_price": 3500, "description": "Complete 30-point checkup, fluid top-up & inspection."},
        {"name": "Brake System Overhaul & Bleeding", "default_price": 2500, "description": "Brake pad replacement, rotor skimming & fluid flush."},
        {"name": "3D Wheel Alignment & Balancing", "default_price": 1500, "description": "Laser wheel alignment and dynamic balancing."},
        {"name": "Computer OBD-II Diagnostic Scan", "default_price": 1000, "description": "Full ECU fault code scanning & clear error logs."},
    ]

    services = []
    for s_data in services_data:
        s, _ = Service.objects.get_or_create(
            user=irtiza,
            name=s_data["name"],
            defaults=s_data
        )
        services.append(s)
    print(f"Seeded {len(services)} service catalog items.")

    # 6. Sample Job Cards
    # Job 1: Completed & Paid
    j1, c1 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[0],
        defaults={
            "customer": customers[0],
            "problem_description": "Scheduled 40,000km periodic maintenance service + engine oil change.",
            "status": "Completed",
            "mileage": "41,250 km"
        }
    )
    if c1:
        JobLabour.objects.create(job_card=j1, description="Periodic Maintenance Labor", cost=3500)
        JobPart.objects.create(job_card=j1, part=parts[0], quantity=1, price_at_time=6000)
        JobPart.objects.create(job_card=j1, part=parts[4], quantity=1, price_at_time=1000)
        tot1 = j1.calculate_total_cost()
        Invoice.objects.create(job_card=j1, total_amount=tot1, amount_paid=tot1, payment_status='Paid')

    # Job 2: In Progress
    j2, c2 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[1],
        defaults={
            "customer": customers[1],
            "problem_description": "Front brake squeal noise under heavy braking. Check pads & rotors.",
            "status": "In Progress",
            "mileage": "28,400 km"
        }
    )
    if c2:
        JobLabour.objects.create(job_card=j2, description="Brake Pad Replacement & Rotor Skimming", cost=2500)
        JobPart.objects.create(job_card=j2, part=parts[1], quantity=1, price_at_time=4500)
        tot2 = j2.calculate_total_cost()
        Invoice.objects.create(job_card=j2, total_amount=tot2, amount_paid=3000, payment_status='Partial')

    # Job 3: Pending
    j3, c3 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[2],
        defaults={
            "customer": customers[2],
            "problem_description": "Engine misfire code P0300. Check spark plugs and ignition coils.",
            "status": "Pending",
            "mileage": "55,100 km"
        }
    )
    if c3:
        JobLabour.objects.create(job_card=j3, description="OBD Scan & Diagnostics Labor", cost=1000)
        tot3 = j3.calculate_total_cost()
        Invoice.objects.create(job_card=j3, total_amount=tot3, amount_paid=0, payment_status='Unpaid')

    print("Successfully seeded all dummy data for Irtiza!")

if __name__ == '__main__':
    seed()
