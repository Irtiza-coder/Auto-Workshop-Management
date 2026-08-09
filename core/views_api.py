import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.utils import timezone
from .models import Customer, Vehicle, Part, Service, JobCard, JobPart, JobLabour, Invoice

def api_response(data=None, message="Success", success=True, status=200):
    res = JsonResponse({
        'success': success,
        'message': message,
        'data': data
    }, status=status)
    res["Access-Control-Allow-Origin"] = "*"
    res["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    res["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return res

@csrf_exempt
def api_login(request):
    if request.method == 'OPTIONS':
        return api_response()
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            username = body.get('username', '').strip()
            password = body.get('password', '').strip()
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return api_response({
                    'username': user.username,
                    'user_id': user.id
                }, message="Login successful")
            return api_response(message="Invalid credentials", success=False, status=400)
        except Exception as e:
            return api_response(message=str(e), success=False, status=400)
    return api_response(message="POST method required", success=False, status=405)

def get_user_or_default(request):
    if request.user and request.user.is_authenticated:
        return request.user
    
    user_id = request.headers.get('X-User-Id') or request.GET.get('user_id')
    from django.contrib.auth.models import User
    if user_id:
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            pass
            
    # Fallback to user with active job cards (e.g. Irtiza), or first user
    user_with_jobs = User.objects.filter(job_cards__isnull=False).distinct().first()
    return user_with_jobs or User.objects.first()


def api_dashboard(request):
    user = get_user_or_default(request)
    jobs = JobCard.objects.all() if not user else JobCard.objects.filter(user=user)
    
    active_jobs = jobs.filter(status__in=['Pending', 'In Progress']).count()
    completed_jobs = jobs.filter(status='Completed').count()
    total_jobs = jobs.count()
    
    total_revenue = sum(
        float(job.invoice.total_amount) for job in jobs if hasattr(job, 'invoice') and job.invoice
    )
    
    customers_count = Customer.objects.count() if not user else Customer.objects.filter(user=user).count()
    parts_low = Part.objects.filter(quantity__lt=5).count()
    
    recent_jobs_data = []
    for j in jobs.order_by('-created_at')[:10]:
        recent_jobs_data.append({
            'id': j.id,
            'customer': j.customer.name,
            'vehicle': f"{j.vehicle.make} {j.vehicle.model}",
            'plate': j.vehicle.number_plate,
            'status': j.status,
            'total': float(j.calculate_total_cost()),
            'date': j.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return api_response({
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'total_jobs': total_jobs,
        'total_revenue': float(total_revenue),
        'total_customers': customers_count,
        'low_stock_parts': parts_low,
        'recent_jobs': recent_jobs_data
    })

def api_jobs(request):
    user = get_user_or_default(request)
    jobs = JobCard.objects.all() if not user else JobCard.objects.filter(user=user)
    
    q = request.GET.get('q', '').strip().lower()
    jobs_data = []
    for j in jobs.order_by('-created_at'):
        cust_name = j.customer.name
        plate = j.vehicle.number_plate
        make_model = f"{j.vehicle.make} {j.vehicle.model}"
        
        if q and not (q in cust_name.lower() or q in plate.lower() or q in make_model.lower()):
            continue

        jobs_data.append({
            'id': j.id,
            'customer': cust_name,
            'customer_phone': j.customer.phone_number,
            'vehicle': make_model,
            'plate': plate,
            'problem': j.problem_description,
            'status': j.status,
            'mileage': j.mileage,
            'total': float(j.calculate_total_cost()),
            'payment_status': j.payment_status,
            'created_at': j.created_at.strftime('%b %d, %Y %I:%M %p')
        })
    return api_response(jobs_data)

def api_job_detail(request, pk):
    try:
        j = JobCard.objects.get(pk=pk)
    except JobCard.DoesNotExist:
        return api_response(message="Job Card not found", success=False, status=404)

    parts_used = []
    for jp in j.job_parts.all():
        parts_used.append({
            'id': jp.id,
            'part_id': jp.part.id,
            'name': jp.part.name,
            'qty': jp.quantity,
            'price': float(jp.price_at_time),
            'total': float(jp.get_cost())
        })

    labours_used = []
    for jl in j.job_labours.all():
        labours_used.append({
            'id': jl.id,
            'description': jl.description,
            'cost': float(jl.cost)
        })

    return api_response({
        'id': j.id,
        'customer_id': j.customer.id,
        'customer_name': j.customer.name,
        'customer_phone': j.customer.phone_number,
        'vehicle_make': j.vehicle.make,
        'vehicle_model': j.vehicle.model,
        'vehicle_plate': j.vehicle.number_plate,
        'problem': j.problem_description,
        'status': j.status,
        'mileage': j.mileage,
        'parts_cost': float(j.total_parts_cost()),
        'labour_cost': float(j.total_labour_cost()),
        'grand_total': float(j.calculate_total_cost()),
        'payment_status': j.payment_status,
        'created_at': j.created_at.strftime('%b %d, %Y %I:%M %p'),
        'parts': parts_used,
        'labours': labours_used
    })

@csrf_exempt
def api_new_job(request):
    if request.method != 'POST':
        return api_response(message="POST required", success=False, status=405)
    
    try:
        body = json.loads(request.body.decode('utf-8'))
        user = get_user_or_default(request)
        
        name = body.get('customer_name', '').strip().upper()
        phone = body.get('customer_phone', '').strip().upper()
        make = body.get('vehicle_make', '').strip().upper()
        model = body.get('vehicle_model', '').strip().upper()
        plate = body.get('vehicle_plate', '').strip().upper()
        problem = body.get('problem_description', '').strip().upper()

        if not all([name, phone, make, model, plate, problem]):
            return api_response(message="All fields are required", success=False, status=400)

        customer, _ = Customer.objects.get_or_create(
            phone_number=phone,
            defaults={'name': name, 'user': user}
        )

        vehicle, _ = Vehicle.objects.get_or_create(
            number_plate=plate,
            defaults={'customer': customer, 'make': make, 'model': model}
        )

        job = JobCard.objects.create(
            user=user,
            customer=customer,
            vehicle=vehicle,
            problem_description=problem,
            status='Pending'
        )

        return api_response({'id': job.id}, message=f"Job #{job.id} created successfully!")
    except Exception as e:
        return api_response(message=str(e), success=False, status=400)

@csrf_exempt
def api_add_part(request, pk):
    if request.method != 'POST':
        return api_response(message="POST required", success=False, status=405)
    try:
        j = JobCard.objects.get(pk=pk)
        body = json.loads(request.body.decode('utf-8'))
        part_id = body.get('part_id')
        qty = int(body.get('quantity', 1))

        part = Part.objects.get(pk=part_id)
        if part.quantity >= qty:
            existing_jp = JobPart.objects.filter(job_card=j, part=part).first()
            if existing_jp:
                existing_jp.quantity += qty
                existing_jp.save()
            else:
                JobPart.objects.create(job_card=j, part=part, quantity=qty, price_at_time=part.price)
            part.quantity -= qty
            part.save()
            return api_response(message=f"Added {qty}x {part.name} to job.")
        else:
            return api_response(message=f"Only {part.quantity} units available in stock!", success=False, status=400)
    except Exception as e:
        return api_response(message=str(e), success=False, status=400)

@csrf_exempt
def api_add_labour(request, pk):
    if request.method != 'POST':
        return api_response(message="POST required", success=False, status=405)
    try:
        j = JobCard.objects.get(pk=pk)
        body = json.loads(request.body.decode('utf-8'))
        desc = body.get('description', '').strip().upper()
        cost = Decimal(str(body.get('cost', 0)))

        if not desc or cost <= 0:
            return api_response(message="Valid description and cost > 0 required", success=False, status=400)

        if JobLabour.objects.filter(job_card=j, description__iexact=desc).exists():
            return api_response(message=f"⚠️ Labour item '{desc}' is ALREADY included in this job!", success=False, status=400)

        JobLabour.objects.create(job_card=j, description=desc, cost=cost)
        return api_response(message=f"Added labour item '{desc}' — Rs.{cost}")
    except Exception as e:
        return api_response(message=str(e), success=False, status=400)

@csrf_exempt
def api_update_status(request, pk):
    if request.method != 'POST':
        return api_response(message="POST required", success=False, status=405)
    try:
        j = JobCard.objects.get(pk=pk)
        body = json.loads(request.body.decode('utf-8'))
        new_status = body.get('status')
        if new_status in ['Pending', 'In Progress', 'Completed']:
            j.status = new_status
            j.save()
            if new_status == 'Completed':
                total = j.calculate_total_cost()
                invoice, created = Invoice.objects.get_or_create(job_card=j, defaults={'total_amount': total})
                if not created:
                    invoice.total_amount = total
                    invoice.save()
            return api_response(message=f"Job status updated to {new_status}")
        return api_response(message="Invalid status", success=False, status=400)
    except Exception as e:
        return api_response(message=str(e), success=False, status=400)

def api_customers(request):
    user = get_user_or_default(request)
    customers = Customer.objects.all() if not user else Customer.objects.filter(user=user)
    
    cust_data = []
    for c in customers.order_by('-created_at'):
        jobs = c.job_cards.all()
        spent = sum(float(j.calculate_total_cost()) for j in jobs)
        cust_data.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone_number,
            'vehicles_count': c.vehicles.count(),
            'jobs_count': jobs.count(),
            'total_spent': float(spent)
        })
    return api_response(cust_data)

def api_inventory(request):
    user = get_user_or_default(request)
    parts = Part.objects.all() if not user else Part.objects.filter(user=user)
    
    parts_data = []
    for p in parts.order_by('name'):
        parts_data.append({
            'id': p.id,
            'name': p.name,
            'company': p.company_name,
            'category': p.category,
            'qty': p.quantity,
            'price': float(p.price),
            'buying_price': float(p.buying_price),
            'low_stock': p.is_low_stock
        })
    return api_response(parts_data)

def api_services(request):
    user = get_user_or_default(request)
    services = Service.objects.all() if not user else Service.objects.filter(user=user)
    
    svc_data = []
    for s in services.order_by('name'):
        svc_data.append({
            'id': s.id,
            'name': s.name,
            'price': float(s.default_price),
            'desc': s.description
        })
    return api_response(svc_data)

@csrf_exempt
def api_sync(request):
    """Batch Sync Endpoint for Offline Actions Queue"""
    if request.method != 'POST':
        return api_response(message="POST required", success=False, status=405)
    
    try:
        body = json.loads(request.body.decode('utf-8'))
        actions = body.get('actions', [])
        synced_count = 0
        errors = []

        with transaction.atomic():
            for act in actions:
                action_type = act.get('type')
                payload = act.get('payload', {})

                if action_type == 'new_job':
                    name = payload.get('customer_name', '').strip().upper()
                    phone = payload.get('customer_phone', '').strip().upper()
                    make = payload.get('vehicle_make', '').strip().upper()
                    model = payload.get('vehicle_model', '').strip().upper()
                    plate = payload.get('vehicle_plate', '').strip().upper()
                    problem = payload.get('problem_description', '').strip().upper()

                    customer, _ = Customer.objects.get_or_create(phone_number=phone, defaults={'name': name})
                    vehicle, _ = Vehicle.objects.get_or_create(number_plate=plate, defaults={'customer': customer, 'make': make, 'model': model})
                    JobCard.objects.create(customer=customer, vehicle=vehicle, problem_description=problem, status='Pending')
                    synced_count += 1

                elif action_type == 'add_part':
                    job_id = payload.get('job_id')
                    part_id = payload.get('part_id')
                    qty = int(payload.get('quantity', 1))
                    j = JobCard.objects.get(pk=job_id)
                    p = Part.objects.get(pk=part_id)
                    existing_jp = JobPart.objects.filter(job_card=j, part=p).first()
                    if existing_jp:
                        existing_jp.quantity += qty
                        existing_jp.save()
                    else:
                        JobPart.objects.create(job_card=j, part=p, quantity=qty, price_at_time=p.price)
                    p.quantity = max(0, p.quantity - qty)
                    p.save()
                    synced_count += 1

                elif action_type == 'add_labour':
                    job_id = payload.get('job_id')
                    desc = payload.get('description', '').strip().upper()
                    cost = Decimal(str(payload.get('cost', 0)))
                    j = JobCard.objects.get(pk=job_id)
                    if not JobLabour.objects.filter(job_card=j, description__iexact=desc).exists():
                        JobLabour.objects.create(job_card=j, description=desc, cost=cost)
                        synced_count += 1

                elif action_type == 'update_status':
                    job_id = payload.get('job_id')
                    new_status = payload.get('status')
                    j = JobCard.objects.get(pk=job_id)
                    j.status = new_status
                    j.save()
                    if new_status == 'Completed':
                        total = j.calculate_total_cost()
                        invoice, created = Invoice.objects.get_or_create(job_card=j, defaults={'total_amount': total})
                        if not created:
                            invoice.total_amount = total
                            invoice.save()
                    synced_count += 1

        return api_response({
            'synced_count': synced_count,
            'errors': errors
        }, message=f"Successfully synced {synced_count} offline actions!")
    except Exception as e:
        return api_response(message=str(e), success=False, status=400)

from django.shortcuts import render
from django.http import FileResponse
import os
from django.conf import settings

def mobile_view(request):
    return render(request, 'core/mobile_app.html')

def manifest_view(request):
    path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    return FileResponse(open(path, 'rb'), content_type='application/json')

def sw_view(request):
    path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    return FileResponse(open(path, 'rb'), content_type='application/javascript')
