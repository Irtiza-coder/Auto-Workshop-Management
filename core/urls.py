from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, views_api

urlpatterns = [
    # Root
    path('', views.root_redirect, name='home'),

    # Auth
    path('login/',           auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/',          auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/',          views.signup,          name='signup'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-username/', views.change_username, name='change_username'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Customers & Vehicles
    path('customers/',                               views.customer_list,        name='customer_list'),
    path('customers/<int:customer_id>/',             views.customer_detail,      name='customer_detail'),
    path('customers/<int:customer_id>/new-job/',     views.new_job_for_customer, name='new_job_for_customer'),
    path('customers/<int:customer_id>/edit/',        views.edit_customer,        name='edit_customer'),
    path('customers/<int:customer_id>/delete/',      views.delete_customer,      name='delete_customer'),
    path('add-vehicle/',                             views.add_vehicle,          name='add_vehicle'),

    # Job Cards
    path('jobs/',                    views.jobcard_list,   name='jobcard_list'),
    path('jobs/<int:pk>/',           views.jobcard_detail, name='jobcard_detail'),
    path('jobs/<int:pk>/delete/',    views.delete_job,     name='delete_job'),
    path('jobs/<int:pk>/invoice/',   views.generate_invoice, name='generate_invoice'),
    path('jobs/<int:pk>/print/',     views.jobcard_print,  name='jobcard_print'),

    # Inventory
    path('inventory/export-csv/',    views.export_inventory_csv, name='export_inventory_csv'),
    path('inventory/',               views.inventory_list,       name='inventory_list'),

    # Services Catalog
    path('services/', views.service_list, name='service_list'),

    # Revenue
    path('revenue/', views.revenue_summary, name='revenue_summary'),

    # Settings
    path('settings/', views.settings_view, name='settings'),



    # --- REST API ENDPOINTS FOR MOBILE APP ---
    path('api/login/',                   views_api.api_login,          name='api_login'),
    path('api/dashboard/',               views_api.api_dashboard,      name='api_dashboard'),
    path('api/jobs/',                    views_api.api_jobs,           name='api_jobs'),
    path('api/jobs/<int:pk>/',           views_api.api_job_detail,     name='api_job_detail'),
    path('api/jobs/new/',                views_api.api_new_job,        name='api_new_job'),
    path('api/jobs/<int:pk>/add-part/',   views_api.api_add_part,       name='api_add_part'),
    path('api/jobs/<int:pk>/add-labour/', views_api.api_add_labour,     name='api_add_labour'),
    path('api/jobs/<int:pk>/status/',    views_api.api_update_status,  name='api_update_status'),
    path('api/customers/',               views_api.api_customers,      name='api_customers'),
    path('api/inventory/',               views_api.api_inventory,      name='api_inventory'),
    path('api/inventory/add/',           views_api.api_add_inventory,  name='api_add_inventory'),
    path('api/services/',                views_api.api_services,       name='api_services'),
    path('api/services/add/',             views_api.api_add_service,    name='api_add_service'),
    path('api/sync/',                    views_api.api_sync,           name='api_sync'),

    # --- MOBILE APP & PWA MANIFEST / SERVICE WORKER ---
    path('mobile/',                      views_api.mobile_view,        name='mobile_app'),
    path('manifest.json',                views_api.manifest_view,      name='manifest_view'),
    path('sw.js',                        views_api.sw_view,            name='sw_view'),
]


