"""This contains all of the database models for the catalog application."""

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User

import datetime
from datetime import date


class HealthStatus(models.Model):
    """Model representing the available domain health settings."""
    health_status = models.CharField(max_length=20, unique=True, help_text='Health status type (e.g. Healthy, Burned)')

    class Meta:
        """Metadata for the model."""
        ordering = ['health_status']
        verbose_name = 'Health status'
        verbose_name_plural = 'Health statuses'
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.health_status


class DomainStatus(models.Model):
    """Model representing the available domain statuses."""
    domain_status = models.CharField(max_length=20, unique=True, help_text='Domain status type (e.g. Available)')

    class Meta:
        """Metadata for the model."""
        ordering = ['domain_status']
        verbose_name = 'Domain status'
        verbose_name_plural = 'Domain statuses'
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.domain_status


class WhoisStatus(models.Model):
    """Model representing the available WHOIS privacy statuses."""
    whois_status = models.CharField(max_length=20, unique=True, help_text='WHOIS privacy status (e.g. Enabled, Disabled)')

    class Meta:
        """Metadata for the model."""
        ordering = ['whois_status']
        verbose_name = 'WHOIS status'
        verbose_name_plural = 'WHOIS statuses'
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.whois_status


class ActivityType(models.Model):
    """Model representing the available domain activity types."""
    activity = models.CharField(max_length=100, unique=True, help_text='Enter a reason for the use of the domain (e.g. command-and-control)')

    class Meta:
        """Metadata for the model."""
        ordering = ['activity']
        verbose_name = 'Domain activity'
        verbose_name_plural = 'Domain activities'
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.activity


class ProjectType(models.Model):
    """Model representing the available project types."""
    project_type = models.CharField('Project Type', max_length=100, unique=True, help_text='Enter a project type (e.g. red team, penetration test)')

    class Meta:
        """Metadata for the model."""
        ordering = ['project_type']
        verbose_name = 'Project type'
        verbose_name_plural = 'Project types'
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.project_type


class Client(models.Model):
    """Model representing the clients attached to project records. This model tracks client
    information. Addition details can be added beyond the client's name, but it likely
    unnecessary for the catalog.
    """
    name = models.CharField('Client Name', max_length=100, unique=True, help_text='Enter the name of the client')

    class Meta:
        """Metadata for the model."""
        ordering = ['name']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.name


class Domain(models.Model):
    """Model representing the domains and related information. This is the primary model for the
    catalog application. This model keeps a record of the domain name and the domain's health,
    categories, and current status (e.g. Available).

    The availability and health statuses are Foreign Keys.
    """
    name = models.CharField('Name', max_length=100, unique=True, help_text='Enter a domain name')
    registrar = models.CharField('Registrar', max_length=100, unique=True, help_text='Enter the name of the registrar where this domain is registered', null=True)
    dns_record = models.CharField('DNS Record', max_length=500, help_text='Enter domain DNS records', null=True)
    health_dns = models.CharField('DNS Health', max_length=100, help_text='Domain health status based on passive DNS (e.g. Healthy, Burned)', null=True)
    creation = models.DateField('Purchase Date', help_text='Domain purchase date')
    expiration = models.DateField('Expiration Date', help_text='Domain expiration date')
    all_cat = models.TextField('All Categories', help_text='All categories applied to this domain', null=True)
    ibm_xforce_cat = models.CharField('IBM X-Force', max_length=100, help_text='Domain category as determined by IBM X-Force', null=True)
    talos_cat = models.CharField('Cisco Talos', max_length=100, help_text='Domain category as determined by Cisco Talos', null=True)
    bluecoat_cat =models.CharField('Bluecoat', max_length=100, help_text='Domain category as determined by Bluecoat', null=True)
    fortiguard_cat = models.CharField('Fortiguard', max_length=100, help_text='Domain category as determined by Fortiguard', null=True)
    opendns_cat = models.CharField('OpenDNS', max_length=100, help_text='Domain category as determined by OpenDNS', null=True)
    trendmicro_cat = models.CharField('TrendMicro', max_length=100, help_text='Domain category as determined by TrendMicro', null=True)
    mx_toolbox_status =  models.CharField('MX Toolbox Status', max_length=100, help_text='Domain spam status as determined by MX Toolbox', null=True)
    note = models.TextField('Notes', help_text='Domain-related notes, such as thoughts behind its purchase or how/why it was burned or retired', null=True)
    burned_explanation = models.TextField('Health Explanation', help_text='Reasons why the domain\'s health status is not "Healthy"', null=True)
    # Foreign Keys
    whois_status = models.ForeignKey('WhoisStatus', on_delete=models.PROTECT, null=True)
    health_status = models.ForeignKey('HealthStatus', on_delete=models.PROTECT, null=True)
    domain_status = models.ForeignKey('DomainStatus', on_delete=models.PROTECT, null=True)
    last_used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['health_status', 'name']
        permissions = (('can_retire_domain', 'Can retire a domain'), ('can_mark_reserved', 'Can reserve a domain'),)
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
         # Adds a "View on Site" button to the model's record editing screens in the Admin site
        return reverse('domain-detail', args=[str(self.id)])

    def get_domain_age(self):
        """Calculate the domain's age based on the current date and the domain's purchase date."""
        time_delta = datetime.date.today() - self.creation
        return time_delta.days

    @property
    def get_list(self):
        """Property to enable fetching the list from the dns_record entry."""
        if self.dns_record:
            return self.dns_record.split(' ::: ')
        else:
            None
    
    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.name} ({self.health_status})'


class History(models.Model):
    """Model representing the project history. This model records start and end dates for a project
    and then uses Foreign Keys for linking the dates to a client, project type, activity type, and
    domain.
    """
    # This field is automatically filled with the current date at check-out
    start_date = models.DateField('Start Date', auto_now_add=True, max_length=100, help_text='Enter the start date of the project')
    end_date = models.DateField('End Date', max_length=100, help_text='Enter the end date of the project')
    note = models.TextField('Notes', help_text='Project-related notes, such as how the domain will be used/how it worked out', null=True)
    slack_channel =  models.CharField('Project Slack Channel', max_length=100, help_text='Name of the Slack channel to be used for updates for this domain during the project\'s duration', null=True)
    # Foreign Keys
    client = models.ForeignKey('Client', on_delete=models.CASCADE, null=False)
    domain = models.ForeignKey('Domain', on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    project_type = models.ForeignKey('ProjectType', on_delete=models.PROTECT, null=False)
    activity_type = models.ForeignKey('ActivityType', on_delete=models.PROTECT, null=False, blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['client', 'domain']
        verbose_name = 'Historical project'
        verbose_name_plural = 'Historical projects'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
         # Adds a "View on Site" button to the model's record editing screens in the Admin site
        return reverse('history_update', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.client} {self.project_type.project_type} - {self.domain.name} ({self.activity_type.activity}) {self.start_date} to {self.end_date} - {self.operator}'

    @property
    def is_overdue(self):
        """Property to test if the provided end date is in the past."""
        if self.start_date and date.today() > self.end_date:
            return True
        return False
