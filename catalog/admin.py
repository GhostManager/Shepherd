"""This contains customizations for the models in the Django admin panel."""

from django.contrib import admin
from catalog.models import Domain, HealthStatus, DomainStatus, WhoisStatus, ActivityType, ProjectType, Client, History


# Define the admin classes and register models
@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain_status', 'name', 'whois_status', 'health_status', 'health_dns', 'note')
    list_filter = ('domain_status',)
    fieldsets = (
        (None, {
            'fields': ('name', 'domain_status', 'creation', 'expiration')
        }),
        ('Health Statuses', {
            'fields': ('whois_status', 'health_status', 'health_dns')
        }),
        ('Categories', {
            'fields': ('all_cat', 'ibm_xforce_cat', 'talos_cat', 'bluecoat_cat', 'fortiguard_cat', 'opendns_cat', 'trendmicro_cat')
        }),
        ('Email and Spam', {
            'fields': ('mx_toolbox_status',)
        }),
        ('Misc', {
            'fields': ('note',)
        })
    )


@admin.register(DomainStatus)
class DomainStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(HealthStatus)
class HealthStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(WhoisStatus)
class WhoisStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    pass


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('client', 'domain', 'activity_type', 'end_date', 'operator')
