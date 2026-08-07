import csv
import os
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum, Q, ProtectedError
from django.conf import settings
from .models import JobCard, Part, JobPart, JobLabour, Invoice, Customer, Vehicle, Service

from django.template.loader import get_template
# pyrefly: ignore [missing-import]
from xhtml2pdf import pisa


# --- Root redirect ---
def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


# --- Admin / Dashboard Views ---
@login_required
def dashboard(request):
    import calendar
    today = timezone.now().date()

    total_jobs_today = JobCard.objects.filter(user=request.user, created_at__date=today).count()
    completed_jobs   = JobCard.objects.filter(user=request.user, status='Completed').count()
    pending_jobs     = JobCard.objects.filter(user=request.user, status='Pending').count()
    in_progress_jobs = JobCard.objects.filter(user=request.user, status='In Progress').count()

    # Calculate current month's profit (automatically resets every month)
    monthly_profit = 0
    for inv in Invoice.objects.filter(
        job_card__user=request.user, created_at__month=today.month, created_at__year=today.year
    ).select_related('job_card').prefetch_related(
        'job_card__job_parts__part', 'job_card__job_labours'
    ).all():
        job = inv.job_card
        for jp in job.job_parts.all():
            monthly_profit += float((jp.price_at_time - jp.part.buying_price) * jp.quantity)
        monthly_profit += float(sum(jl.cost for jl in job.job_labours.all()))
    total_revenue = monthly_profit

    # Calculate last 6 months profit trend & job counts for Chart.js
    monthly_labels  = []
    monthly_profits = []
    monthly_jobs    = []
    curr_year       = today.year
    curr_month      = today.month

    for i in range(5, -1, -1):
        m = curr_month - i
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1

        month_label = f"{calendar.month_abbr[m]} {y}"
        monthly_labels.append(month_label)

        # Real profit calculation
        m_profit = 0
        for inv in Invoice.objects.filter(
            job_card__user=request.user,
            created_at__month=m,
            created_at__year=y
        ).select_related('job_card').prefetch_related(
            'job_card__job_parts__part', 'job_card__job_labours'
        ).all():
            job = inv.job_card
            for jp in job.job_parts.all():
                m_profit += float((jp.price_at_time - jp.part.buying_price) * jp.quantity)
            m_profit += float(sum(jl.cost for jl in job.job_labours.all()))
        monthly_profits.append(round(m_profit, 2))

        # Real jobs count calculation
        m_job_count = JobCard.objects.filter(
            user=request.user,
            created_at__year=y,
            created_at__month=m
        ).count()
        monthly_jobs.append(m_job_count)

    recent_jobs     = JobCard.objects.filter(user=request.user).select_related('customer', 'vehicle', 'invoice').order_by('-created_at')[:8]
    total_customers = Customer.objects.filter(user=request.user).count()
    low_stock_parts = Part.objects.filter(user=request.user, quantity__lt=5).count()

    context = {
        'total_jobs_today': total_jobs_today,
        'completed_jobs':   completed_jobs,
        'pending_jobs':     pending_jobs,
        'in_progress_jobs': in_progress_jobs,
        'total_revenue':    total_revenue,
        'monthly_labels':   monthly_labels,
        'monthly_profits':  monthly_profits,
        'monthly_jobs':     monthly_jobs,
        'recent_jobs':      recent_jobs,
        'total_customers':  total_customers,
        'low_stock_parts':  low_stock_parts,
    }
    return render(request, 'core/dashboard.html', context)



# --- Customer & Vehicle Management ---
@login_required
def customer_list(request):
    query = request.GET.get('q', '').strip()
    customers = Customer.objects.filter(user=request.user).prefetch_related('vehicles').order_by('id')

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(vehicles__number_plate__icontains=query)
        ).distinct()
    return render(request, 'core/customer_list.html', {'customers': customers, 'query': query})


@login_required
def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
    vehicles = customer.vehicles.all()
    jobs     = customer.job_cards.select_related('vehicle', 'invoice').order_by('-created_at')

    total_jobs     = jobs.count()
    completed_jobs = jobs.filter(status='Completed').count()
    active_jobs    = jobs.filter(status__in=['Pending', 'In Progress']).count()

    total_spent = sum(
        float(job.invoice.total_amount) for job in jobs if hasattr(job, 'invoice') and job.invoice
    )

    context = {
        'customer':       customer,
        'vehicles':       vehicles,
        'jobs':           jobs,
        'total_jobs':     total_jobs,
        'completed_jobs': completed_jobs,
        'active_jobs':    active_jobs,
        'total_spent':    total_spent,
    }
    return render(request, 'core/customer_detail.html', context)




@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
    if request.method == 'POST':
        name  = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        if name and phone:
            customer.name         = name
            customer.phone_number = phone
            customer.save()
            messages.success(request, f'✅ Customer "{name}" updated.')
        else:
            messages.error(request, 'Name and phone are required.')
    return redirect('customer_list')


@login_required
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
    if request.method == 'POST':
        name = customer.name
        customer.delete()
        messages.success(request, f'🗑️ Customer "{name}" and all their records deleted.')
    return redirect('customer_list')


@login_required
def add_vehicle(request):
    """Admin adds a customer + vehicle entry, then optionally creates a job."""
    if request.method == 'POST':
        # Customer info
        customer_name  = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        # Vehicle info
        vehicle_make   = request.POST.get('vehicle_make', '').strip()
        vehicle_model  = request.POST.get('vehicle_model', '').strip()
        vehicle_plate  = request.POST.get('vehicle_plate', '').strip().upper()
        # Job info
        problem_desc   = request.POST.get('problem_description', '').strip()

        if not all([customer_name, customer_phone, vehicle_make, vehicle_model, vehicle_plate, problem_desc]):
            messages.error(request, 'All fields are required.')
            return redirect('add_vehicle')

        # Get or create customer for this user
        customer, _ = Customer.objects.get_or_create(
            phone_number=customer_phone,
            user=request.user,
            defaults={'name': customer_name}
        )

        # Check if plate already exists for this user's customer
        if Vehicle.objects.filter(number_plate=vehicle_plate, customer__user=request.user).exists():
            vehicle = Vehicle.objects.get(number_plate=vehicle_plate, customer__user=request.user)
            messages.warning(request, f'Vehicle {vehicle_plate} already exists — linked to existing record.')
        else:
            vehicle = Vehicle.objects.create(
                customer=customer,
                make=vehicle_make,
                model=vehicle_model,
                number_plate=vehicle_plate
            )

        # Create job card
        job = JobCard.objects.create(
            user=request.user,
            customer=customer,
            vehicle=vehicle,
            problem_description=problem_desc,
            status='Pending'
        )
        messages.success(request, f'✅ Job #{job.id} created for {customer.name} — {vehicle_plate}')
        return redirect('jobcard_detail', pk=job.pk)

    return render(request, 'core/add_vehicle.html')


@login_required
def new_job_for_customer(request, customer_id):
    """Admin picks an existing vehicle or adds a new one for a known customer."""
    customer = get_object_or_404(Customer, pk=customer_id, user=request.user)
    vehicles = customer.vehicles.all()

    if request.method == 'POST':
        vehicle_choice = request.POST.get('vehicle_choice')  # 'existing' or 'new'
        problem_desc   = request.POST.get('problem_description', '').strip()

        if not problem_desc:
            messages.error(request, 'Please describe the problem.')
            return redirect('new_job_for_customer', customer_id=customer_id)

        if vehicle_choice == 'new':
            vehicle_make  = request.POST.get('vehicle_make', '').strip()
            vehicle_model = request.POST.get('vehicle_model', '').strip()
            vehicle_plate = request.POST.get('vehicle_plate', '').strip().upper()

            if not all([vehicle_make, vehicle_model, vehicle_plate]):
                messages.error(request, 'Please fill in all new vehicle fields.')
                return redirect('new_job_for_customer', customer_id=customer_id)

            if Vehicle.objects.filter(number_plate=vehicle_plate, customer__user=request.user).exists():
                vehicle = Vehicle.objects.get(number_plate=vehicle_plate, customer__user=request.user)
                messages.warning(request, f'Plate {vehicle_plate} already exists — linked to existing record.')
            else:
                vehicle = Vehicle.objects.create(
                    customer=customer,
                    make=vehicle_make,
                    model=vehicle_model,
                    number_plate=vehicle_plate
                )
                messages.success(request, f'New vehicle {vehicle_plate} added.')
        else:
            vehicle_id = request.POST.get('vehicle_id')
            vehicle = get_object_or_404(Vehicle, pk=vehicle_id, customer=customer)

        job = JobCard.objects.create(
            user=request.user,
            customer=customer,
            vehicle=vehicle,
            problem_description=problem_desc,
            status='Pending'
        )
        messages.success(request, f'✅ Job #{job.id} created for {customer.name} — {vehicle.number_plate}')
        return redirect('jobcard_detail', pk=job.pk)

    return render(request, 'core/new_job_for_customer.html', {
        'customer': customer,
        'vehicles': vehicles,
    })


# --- Job Card Views ---
@login_required
def jobcard_list(request):
    status_filter = request.GET.get('status', '')
    query         = request.GET.get('q', '').strip()

    jobs = JobCard.objects.filter(user=request.user).select_related('customer', 'vehicle', 'invoice').order_by('-created_at')

    if status_filter and status_filter.lower() != 'all':
        jobs = jobs.filter(status=status_filter)
    if query:
        jobs = jobs.filter(
            Q(customer__name__icontains=query) |
            Q(customer__phone_number__icontains=query) |
            Q(vehicle__number_plate__icontains=query) |
            Q(vehicle__make__icontains=query) |
            Q(vehicle__model__icontains=query)
        ).distinct()

    all_jobs = JobCard.objects.filter(user=request.user)
    counts = {
        'all':         all_jobs.count(),
        'pending':     all_jobs.filter(status='Pending').count(),
        'in_progress': all_jobs.filter(status='In Progress').count(),
        'completed':   all_jobs.filter(status='Completed').count(),
    }

    return render(request, 'core/jobcard_list.html', {
        'jobs': jobs,
        'status_filter': status_filter,
        'query': query,
        'counts': counts,
    })



@login_required
def delete_job(request, pk):
    job = get_object_or_404(JobCard, pk=pk, user=request.user)
    if request.method == 'POST':
        # Restore part stock before deleting
        for jobpart in job.job_parts.all():
            jobpart.part.quantity += jobpart.quantity
            jobpart.part.save()
        job_id = job.id
        job.delete()
        messages.success(request, f'🗑️ Job #{job_id} deleted and stock restored.')
    return redirect('jobcard_list')


@login_required
def jobcard_detail(request, pk):
    job             = get_object_or_404(JobCard, pk=pk, user=request.user)
    parts_available = Part.objects.filter(user=request.user, quantity__gt=0)
    has_invoice     = hasattr(job, 'invoice')
    job_labours     = job.job_labours.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_part':
            part_id = request.POST.get('part_id')
            qty     = int(request.POST.get('quantity', 1))
            part    = get_object_or_404(Part, pk=part_id, user=request.user)

            if part.quantity >= qty:
                existing_jp = JobPart.objects.filter(job_card=job, part=part).first()
                if existing_jp:
                    existing_jp.quantity += qty
                    existing_jp.save()
                else:
                    JobPart.objects.create(
                        job_card=job,
                        part=part,
                        quantity=qty,
                        price_at_time=part.price
                    )
                part.quantity -= qty
                part.save()
                messages.success(request, f'Added {qty}x {part.name} to job.')
            else:
                messages.error(request, f'Not enough stock! Only {part.quantity} units available.')

        elif action == 'add_labour':
            description = request.POST.get('labour_description', '').strip()
            cost_str    = request.POST.get('labour_cost', '0').strip()
            if description and cost_str:
                try:
                    cost = Decimal(str(cost_str))
                    if cost > 0:
                        if JobLabour.objects.filter(job_card=job, description__iexact=description).exists():
                            messages.warning(request, f'⚠️ Labour item "{description}" is already included in this job.')
                        else:
                            JobLabour.objects.create(job_card=job, description=description, cost=cost)
                            messages.success(request, f'✅ Labour item "{description}" — Rs.{cost} added.')
                    else:
                        messages.error(request, 'Labour cost must be greater than 0.')
                except Exception:
                    messages.error(request, 'Invalid cost amount.')
            else:
                messages.error(request, 'Labour description and cost are required.')

        elif action == 'remove_labour':
            labour_id = request.POST.get('labour_id')
            labour    = get_object_or_404(JobLabour, pk=labour_id, job_card=job)
            desc      = labour.description
            labour.delete()
            messages.success(request, f'Labour item "{desc}" removed.')

        elif action == 'update_status':
            new_status = request.POST.get('status')
            job.status = new_status

            # Update mileage if provided
            mileage = request.POST.get('mileage', '').strip()
            job.mileage = mileage

            job.save()

            # Auto-create/update invoice when Completed; delete when reverted
            if new_status == 'Completed':
                total_calculated = job.calculate_total_cost()
                invoice, created = Invoice.objects.get_or_create(
                    job_card=job,
                    defaults={'total_amount': total_calculated}
                )
                if not created:
                    invoice.total_amount = total_calculated
                    invoice.save()
                messages.success(request, f'Job marked Completed — Rs.{total_calculated} billed, profit recorded.')
            else:
                # Remove invoice if job is moved OUT of Completed
                try:
                    job.invoice.delete()
                    messages.warning(request, f'Job moved to "{new_status}" — revenue entry removed.')
                except Exception:
                    messages.success(request, f'Job status updated to "{new_status}".')

        elif action == 'update_payment':
            if hasattr(job, 'invoice'):
                user_status = request.POST.get('payment_status')
                amount_str  = request.POST.get('amount_paid', '0.00').strip()
                try:
                    amount_paid  = Decimal(amount_str)
                    total_amount = job.invoice.total_amount

                    # Automatic status determination based on amount paid vs total
                    if amount_paid >= total_amount and total_amount > 0:
                        payment_status = 'Paid'
                    elif amount_paid > 0:
                        payment_status = 'Partial'
                    else:
                        payment_status = 'Unpaid'

                    # If user explicitly chose Paid and amount_paid was 0, auto-fill full amount
                    if user_status == 'Paid' and amount_paid < total_amount:
                        amount_paid = total_amount
                        payment_status = 'Paid'

                    job.invoice.payment_status = payment_status
                    job.invoice.amount_paid    = amount_paid
                    job.invoice.save()
                    messages.success(request, f'💳 Payment updated: {payment_status} (Received: Rs.{job.invoice.amount_paid})')
                except Exception as e:
                    messages.error(request, f'Invalid amount format: {e}')
            else:
                messages.error(request, 'Invoice not generated yet. Mark job as Completed first.')

        elif action == 'remove_part':
            jobpart_id = request.POST.get('jobpart_id')
            jobpart    = get_object_or_404(JobPart, pk=jobpart_id, job_card=job)
            # Restore stock
            jobpart.part.quantity += jobpart.quantity
            jobpart.part.save()
            jobpart.delete()
            messages.success(request, 'Part removed from job and stock restored.')

        return redirect('jobcard_detail', pk=job.pk)

    context = {
        'job':              job,
        'parts_available':  parts_available,
        'has_invoice':      has_invoice,
        'job_labours':      job_labours,
        'services_catalog': Service.objects.filter(user=request.user).order_by('name'),
    }
    return render(request, 'core/jobcard_detail.html', context)



@login_required
def jobcard_print(request, pk):
    """Render printer-friendly ticket/receipt view."""
    job = get_object_or_404(JobCard, pk=pk, user=request.user)
    return render(request, 'core/jobcard_print.html', {'job': job})


@login_required
def generate_invoice(request, pk):
    job = get_object_or_404(JobCard, pk=pk, user=request.user)

    total_calculated = job.calculate_total_cost()
    invoice, created = Invoice.objects.get_or_create(
        job_card=job,
        defaults={'total_amount': total_calculated}
    )
    if not created and invoice.total_amount != total_calculated:
        invoice.total_amount = total_calculated
        invoice.save()

    logo_b64 = ""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'auto_city_logo.png')
    if os.path.exists(logo_path):
        import base64
        with open(logo_path, 'rb') as img_f:
            logo_b64 = "data:image/png;base64," + base64.b64encode(img_f.read()).decode('utf-8')

    template_path = 'core/invoice_pdf.html'
    context = {'invoice': invoice, 'job': job, 'logo_b64': logo_b64}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="invoice_job_{job.id}.pdf"'

    template    = get_template(template_path)
    html        = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF error: <pre>' + html + '</pre>')
    return response


# --- Revenue Summary ---
@login_required
def revenue_summary(request):
    from datetime import timedelta
    from django.db.models import Sum, Count

    period = request.GET.get('period', 'all')
    today  = timezone.now().date()

    # Base queryset — jobs that have invoices for this user
    invoices = Invoice.objects.filter(job_card__user=request.user).select_related(
        'job_card', 'job_card__customer', 'job_card__vehicle'
    ).order_by('-created_at')

    # Apply period filter
    if period == 'today':
        invoices = invoices.filter(created_at__date=today)
    elif period == 'week':
        invoices = invoices.filter(created_at__date__gte=today - timedelta(days=7))
    elif period == 'month':
        invoices = invoices.filter(created_at__date__gte=today - timedelta(days=30))

    # Build enriched rows
    rows = []
    total_bill_sum       = 0
    total_profit_sum     = 0
    total_parts_bill_sum = 0
    total_parts_cost_sum = 0
    total_labor_sum      = 0

    for inv in invoices:
        job        = inv.job_card
        job_parts  = list(job.job_parts.select_related('part').all())
        job_labour = list(job.job_labours.all())

        parts_bill   = sum(jp.price_at_time * jp.quantity for jp in job_parts)
        parts_cost   = sum(jp.part.buying_price * jp.quantity for jp in job_parts)
        parts_profit = float(parts_bill) - float(parts_cost)
        labor        = float(sum(jl.cost for jl in job_labour))
        bill_total   = float(inv.total_amount)
        profit       = parts_profit + labor

        total_bill_sum       += bill_total
        total_profit_sum     += profit
        total_parts_bill_sum += float(parts_bill)
        total_parts_cost_sum += float(parts_cost)
        total_labor_sum      += labor

        rows.append({
            'invoice':      inv,
            'job':          job,
            'parts_bill':   float(parts_bill),
            'parts_cost':   float(parts_cost),
            'parts_profit': parts_profit,
            'labor':        labor,
            'bill_total':   bill_total,
            'profit':       profit,
        })

    context = {
        'rows':                   rows,
        'period':                 period,
        'total_bill_sum':         total_bill_sum,
        'total_profit_sum':       total_profit_sum,
        'total_parts_bill_sum':   total_parts_bill_sum,
        'total_parts_cost_sum':   total_parts_cost_sum,
        'total_parts_profit_sum': total_parts_bill_sum - total_parts_cost_sum,
        'total_labor_sum':        total_labor_sum,
        'job_count':              len(rows),
        'avg_profit_per_job':     (total_profit_sum / len(rows)) if rows else 0,
    }

    return render(request, 'core/revenue_summary.html', context)


# --- Inventory ---
@login_required
def export_inventory_csv(request):
    """Download current inventory as a CSV spreadsheet."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Part Name', 'Company/Brand', 'Category', 'Quantity', 'Buying Price (Rs.)', 'Selling Price (Rs.)', 'Profit per Unit', 'Stock Status'])

    parts = Part.objects.filter(user=request.user).order_by('name')
    for p in parts:
        status = 'LOW STOCK' if p.is_low_stock else 'In Stock'
        writer.writerow([
            p.id,
            p.name,
            p.company_name,
            p.category,
            p.quantity,
            p.buying_price,
            p.price,
            p.profit_per_unit,
            status,
        ])

    return response


@login_required
def inventory_list(request):
    query     = request.GET.get('q', '').strip()
    low_stock = request.GET.get('low_stock')

    parts = Part.objects.filter(user=request.user).order_by('id')

    if low_stock:
        parts = parts.filter(quantity__lt=5)
    if query:
        parts = parts.filter(
            Q(name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(category__icontains=query)
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_part':
            name          = request.POST.get('name', '').strip()
            volume_liters = request.POST.get('volume_liters', '').strip()
            if volume_liters and 'oil' in name.lower() and 'filter' not in name.lower():
                if not volume_liters.lower().endswith('l'):
                    volume_liters = f"{volume_liters}L"
                if f'({volume_liters})' not in name:
                    name = f"{name} ({volume_liters})"
            company_name  = request.POST.get('company_name', '').strip()
            category      = request.POST.get('category', 'Genuine')
            quantity      = request.POST.get('quantity', '').strip() or 0
            buying_price  = request.POST.get('buying_price', '').strip() or 0
            selling_price = request.POST.get('selling_price', '').strip() or 0
            Part.objects.create(
                user=request.user,
                name=name,
                company_name=company_name,
                category=category,
                quantity=quantity,
                buying_price=buying_price,
                price=selling_price
            )
            messages.success(request, f'✅ "{name}" added to inventory.')
            return redirect('inventory_list')

        elif action == 'update_part':
            part_id           = request.POST.get('part_id')
            part              = get_object_or_404(Part, pk=part_id, user=request.user)
            name              = request.POST.get('name', part.name).strip()
            volume_liters     = request.POST.get('volume_liters', '').strip()
            if volume_liters and 'oil' in name.lower() and 'filter' not in name.lower():
                if not volume_liters.lower().endswith('l'):
                    volume_liters = f"{volume_liters}L"
                if f'({volume_liters})' not in name:
                    name = f"{name} ({volume_liters})"
            part.name         = name
            part.company_name = request.POST.get('company_name', '').strip()
            part.category     = request.POST.get('category', 'Genuine')
            part.quantity     = request.POST.get('quantity', '').strip() or 0
            part.buying_price = request.POST.get('buying_price', '').strip() or 0
            part.price        = request.POST.get('selling_price', '').strip() or 0
            part.save()
            messages.success(request, f'✅ "{part.name}" updated.')
            return redirect('inventory_list')

        elif action == 'delete_part':
            part_id   = request.POST.get('part_id')
            part      = get_object_or_404(Part, pk=part_id, user=request.user)
            part_name = part.name
            try:
                part.delete()
                messages.success(request, f'🗑️ "{part_name}" removed.')
            except ProtectedError:
                messages.error(request, f'⚠️ Cannot delete "{part_name}" because it is linked to existing Job Cards / Invoices.')
            return redirect('inventory_list')

    return render(request, 'core/inventory_list.html', {
        'parts': parts,
        'query': query,
        'low_stock_filtered': bool(low_stock),
    })


# --- Services Catalog ---
@login_required
def service_list(request):
    query    = request.GET.get('q', '').strip()
    services = Service.objects.filter(user=request.user).order_by('id')

    if query:
        services = services.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_service':
            name          = request.POST.get('name', '').strip()
            default_price = request.POST.get('default_price', '0').strip()
            description   = request.POST.get('description', '').strip()

            if name and default_price:
                Service.objects.create(
                    user=request.user,
                    name=name,
                    default_price=Decimal(default_price),
                    description=description
                )
                messages.success(request, f'✅ Service "{name}" added to catalog.')
            else:
                messages.error(request, 'Service name and price are required.')
            return redirect('service_list')

        elif action == 'update_service':
            service_id    = request.POST.get('service_id')
            service       = get_object_or_404(Service, pk=service_id, user=request.user)
            name          = request.POST.get('name', '').strip()
            default_price = request.POST.get('default_price', '0').strip()
            description   = request.POST.get('description', '').strip()

            if name and default_price:
                service.name          = name
                service.default_price = Decimal(default_price)
                service.description   = description
                service.save()
                messages.success(request, f'✅ Service "{name}" updated.')
            else:
                messages.error(request, 'Service name and price are required.')
            return redirect('service_list')

        elif action == 'delete_service':
            service_id   = request.POST.get('service_id')
            service      = get_object_or_404(Service, pk=service_id, user=request.user)
            service_name = service.name
            service.delete()
            messages.success(request, f'🗑️ Service "{service_name}" removed from catalog.')
            return redirect('service_list')

    return render(request, 'core/service_list.html', {
        'services': services,
        'query': query,
    })


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '🔑 Password updated successfully!')
        else:
            for error in form.non_field_errors():
                messages.error(request, f'⚠️ {error}')
            for field, errors in form.errors.items():
                if field != '__all__':
                    for error in errors:
                        messages.error(request, f'⚠️ {field.replace("_", " ").title()}: {error}')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@login_required
def change_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('new_username', '').strip()
        if new_username:
            if new_username == request.user.username:
                messages.info(request, 'Username unchanged.')
            elif User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                messages.error(request, f'⚠️ Username "{new_username}" is already taken.')
            else:
                request.user.username = new_username
                request.user.save()
                messages.success(request, f'👤 Username updated to "{new_username}".')
        else:
            messages.error(request, '⚠️ Username cannot be empty.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()

        if not username or not password:
            messages.error(request, '⚠️ Username and password are required.')
        elif password != password_confirm:
            messages.error(request, '⚠️ Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'⚠️ Username "{username}" is already taken.')
        else:
            user = User.objects.create_user(username=username, password=password)
            from django.contrib.auth import login as auth_login
            auth_login(request, user)
            messages.success(request, f'🎉 Welcome, {username}! Your workshop account has been created.')
            return redirect('dashboard')
    return render(request, 'core/signup.html')


def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not username or not new_password:
            messages.error(request, '⚠️ Username and new password are required.')
        elif new_password != confirm_password:
            messages.error(request, '⚠️ Passwords do not match.')
        elif not User.objects.filter(username=username).exists():
            messages.error(request, f'⚠️ User "{username}" does not exist.')
        else:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            messages.success(request, f'🔑 Password for "{username}" reset successfully! Please log in.')
            return redirect('login')
    return render(request, 'core/forgot_password.html')


@login_required
def settings_view(request):
    all_users = None
    if request.user.is_superuser:
        from django.contrib.auth import get_user_model
        all_users = get_user_model().objects.all().order_by('-date_joined')
    return render(request, 'core/settings.html', {'all_users': all_users})


@login_required
def seed_demo_data_view(request):
    """Populate realistic dummy customers, vehicles, inventory parts, and job cards for Irtiza."""
    from seed_data import seed
    try:
        seed()
        messages.success(request, "🎉 Dummy data for Irtiza (Customers, Vehicles, Parts, Job Cards, Invoices) populated successfully!")
    except Exception as e:
        messages.error(request, f"Error seeding dummy data: {e}")
    return redirect('dashboard')








