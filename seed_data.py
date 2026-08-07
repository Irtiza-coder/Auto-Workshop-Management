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

    print(f"Seeding rich dummy data for user: {irtiza.username}")

    # 2. Customers
    customers_data = [
        {"name": "Muhammad Ali", "phone_number": "0300-1234567"},
        {"name": "Sarah Jenkins", "phone_number": "0321-9876543"},
        {"name": "David Miller", "phone_number": "0312-4567890"},
        {"name": "Ahmed Raza", "phone_number": "0333-5551212"},
        {"name": "Emily Watson", "phone_number": "0345-6789012"},
        {"name": "Hassan Sheikh", "phone_number": "0301-8889900"},
        {"name": "Robert Chen", "phone_number": "0322-7776655"},
        {"name": "Zainab Fatima", "phone_number": "0315-4443322"},
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

    # 3. Vehicles (2 to 3 cars per customer)
    vehicles_data = [
        # Customer 0: Muhammad Ali
        {"customer": customers[0], "make": "Toyota", "model": "Corolla Altis 1.8", "number_plate": "LEC-19-2041"},
        {"customer": customers[0], "make": "Honda", "model": "Civic Rebirth", "number_plate": "ICT-16-5520"},
        {"customer": customers[0], "make": "Suzuki", "model": "Alto VXR", "number_plate": "LHR-22-9011"},

        # Customer 1: Sarah Jenkins
        {"customer": customers[1], "make": "Honda", "model": "Civic Turbo RS", "number_plate": "ICT-22-8840"},
        {"customer": customers[1], "make": "Toyota", "model": "Fortuner Sigma4", "number_plate": "KHI-21-1008"},

        # Customer 2: David Miller
        {"customer": customers[2], "make": "Suzuki", "model": "Swift VXL", "number_plate": "LHR-20-4102"},
        {"customer": customers[2], "make": "Toyota", "model": "Yaris ATIV", "number_plate": "ISB-23-4411"},
        {"customer": customers[2], "make": "KIA", "model": "Picanto Auto", "number_plate": "LEC-21-7730"},

        # Customer 3: Ahmed Raza
        {"customer": customers[3], "make": "Hyundai", "model": "Tucson AWD", "number_plate": "KHI-23-9901"},
        {"customer": customers[3], "make": "Honda", "model": "BR-V i-VTEC", "number_plate": "LHR-18-6200"},

        # Customer 4: Emily Watson
        {"customer": customers[4], "make": "Kia", "model": "Sportage AWD", "number_plate": "ISB-21-3319"},
        {"customer": customers[4], "make": "MG", "model": "HS Trophy", "number_plate": "LEC-22-5599"},

        # Customer 5: Hassan Sheikh
        {"customer": customers[5], "make": "Changan", "model": "Alsvin Lumiere", "number_plate": "LHR-22-3110"},
        {"customer": customers[5], "make": "Toyota", "model": "Hilux Revo", "number_plate": "ISB-20-9988"},
        {"customer": customers[5], "make": "Suzuki", "model": "Cultus VXL", "number_plate": "LEC-19-1122"},

        # Customer 6: Robert Chen
        {"customer": customers[6], "make": "Audi", "model": "A4 1.8 TFSI", "number_plate": "ICT-17-7007"},
        {"customer": customers[6], "make": "BMW", "model": "320i Sedan", "number_plate": "LHR-15-3003"},

        # Customer 7: Zainab Fatima
        {"customer": customers[7], "make": "Honda", "model": "City Aspire 1.5", "number_plate": "KHI-20-8448"},
        {"customer": customers[7], "make": "Toyota", "model": "Passo 1.0", "number_plate": "LEC-18-6621"},
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
    print(f"Seeded {len(vehicles)} vehicles (2-3 cars per customer).")

    # 4. Inventory Spare Parts
    parts_data = [
        {"name": "Synthetic Engine Oil 5W-30 (4L)", "company_name": "Shell Helix Ultra", "category": "Genuine", "quantity": 40, "buying_price": 4500, "price": 6200},
        {"name": "Fully Synthetic 0W-20 (4L)", "company_name": "Mobil 1", "category": "Genuine", "quantity": 25, "buying_price": 5500, "price": 7500},
        {"name": "Front Ceramic Brake Pads", "company_name": "Bosch", "category": "OEM", "quantity": 20, "buying_price": 3200, "price": 4800},
        {"name": "Rear Brake Shoes", "company_name": "Nissin", "category": "Genuine", "quantity": 15, "buying_price": 2200, "price": 3500},
        {"name": "Engine Air Filter Element", "company_name": "Toyota Genuine", "category": "Genuine", "quantity": 50, "buying_price": 1200, "price": 1800},
        {"name": "Cabin AC Air Filter", "company_name": "Denso", "category": "OEM", "quantity": 45, "buying_price": 800, "price": 1400},
        {"name": "Iridium Spark Plugs (Set of 4)", "company_name": "NGK Japan", "category": "Aftermarket", "quantity": 30, "buying_price": 2800, "price": 4200},
        {"name": "Spin-On Oil Filter", "company_name": "Vic Japan", "category": "Genuine", "quantity": 60, "buying_price": 650, "price": 1100},
        {"name": "CVTF Transmission Fluid (4L)", "company_name": "Honda Genuine", "category": "Genuine", "quantity": 18, "buying_price": 6000, "price": 8500},
        {"name": "Radiator Coolant Concentrate (3L)", "company_name": "Caltex Havoline", "category": "OEM", "quantity": 22, "buying_price": 1800, "price": 2600},
        {"name": "DOT 4 Brake Fluid (1L)", "company_name": "Liqui Moly", "category": "Aftermarket", "quantity": 35, "buying_price": 1400, "price": 2100},
        {"name": "Wiper Blades Aerotwin Pair", "company_name": "Bosch", "category": "Aftermarket", "quantity": 28, "buying_price": 1500, "price": 2400},
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

    # 5. Service Catalog
    services_data = [
        {"name": "Full Periodic Maintenance Service", "default_price": 3500, "description": "30-point inspection, engine oil replacement, filter cleaning & fluid top-ups."},
        {"name": "Brake System Overhaul & Rotor Skimming", "default_price": 2800, "description": "Brake pad replacement, disc rotor resurfacing & hydraulic bleeding."},
        {"name": "3D Laser Wheel Alignment & Balancing", "default_price": 1800, "description": "High-precision 3D alignment and 4-wheel dynamic balancing."},
        {"name": "Computer OBD-II ECU Diagnostic Scan", "default_price": 1200, "description": "Full sensor diagnostic scanning, live data analysis & fault clearing."},
        {"name": "Automatic Transmission Fluid Flush", "default_price": 3000, "description": "Full ATF/CVTF fluid evacuation, filter replacement & refill."},
        {"name": "AC Service & Gas Recharge", "default_price": 4000, "description": "Evaporator coil cleaning, leak test & R134a refrigerant refill."},
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

    # 6. Sample Job Cards & Invoices
    # Job 1: Corolla (Muhammad Ali) - Completed & Paid
    j1, c1 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[0],
        defaults={
            "customer": customers[0],
            "problem_description": "Scheduled 40,000km periodic service + synthetic oil change & air filter replacement.",
            "status": "Completed",
            "mileage": "41,250 km"
        }
    )
    if c1:
        JobLabour.objects.create(job_card=j1, description="Periodic Maintenance Labor", cost=3500)
        JobPart.objects.create(job_card=j1, part=parts[0], quantity=1, price_at_time=6200)
        JobPart.objects.create(job_card=j1, part=parts[4], quantity=1, price_at_time=1800)
        JobPart.objects.create(job_card=j1, part=parts[7], quantity=1, price_at_time=1100)
        tot1 = j1.calculate_total_cost()
        Invoice.objects.create(job_card=j1, total_amount=tot1, amount_paid=tot1, payment_status='Paid')

    # Job 2: Civic Turbo (Sarah Jenkins) - In Progress & Partial
    j2, c2 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[3],
        defaults={
            "customer": customers[1],
            "problem_description": "Front brake squeal noise and steering vibration during high speed braking.",
            "status": "In Progress",
            "mileage": "28,400 km"
        }
    )
    if c2:
        JobLabour.objects.create(job_card=j2, description="Brake Pad Replacement & Rotor Skimming", cost=2800)
        JobPart.objects.create(job_card=j2, part=parts[2], quantity=1, price_at_time=4800)
        tot2 = j2.calculate_total_cost()
        Invoice.objects.create(job_card=j2, total_amount=tot2, amount_paid=4000, payment_status='Partial')

    # Job 3: Swift (David Miller) - Pending & Unpaid
    j3, c3 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[5],
        defaults={
            "customer": customers[2],
            "problem_description": "Check engine light illuminated. Engine misfire under acceleration.",
            "status": "Pending",
            "mileage": "55,100 km"
        }
    )
    if c3:
        JobLabour.objects.create(job_card=j3, description="OBD Scan & Ignition Diagnostics", cost=1200)
        tot3 = j3.calculate_total_cost()
        Invoice.objects.create(job_card=j3, total_amount=tot3, amount_paid=0, payment_status='Unpaid')

    # Job 4: Tucson (Ahmed Raza) - Completed & Paid
    j4, c4 = JobCard.objects.get_or_create(
        user=irtiza,
        vehicle=vehicles[8],
        defaults={
            "customer": customers[3],
            "problem_description": "Transmission fluid replacement & 3D wheel alignment.",
            "status": "Completed",
            "mileage": "35,000 km"
        }
    )
    if c4:
        JobLabour.objects.create(job_card=j4, description="ATF Flush & Alignment Labor", cost=3000)
        JobPart.objects.create(job_card=j4, part=parts[8], quantity=1, price_at_time=8500)
        tot4 = j4.calculate_total_cost()
        Invoice.objects.create(job_card=j4, total_amount=tot4, amount_paid=tot4, payment_status='Paid')

    print("Successfully seeded extensive dummy data for Irtiza!")

if __name__ == '__main__':
    seed()
