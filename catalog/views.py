"""This contains all of the views for the catalog application's various webpages."""

# Import logging functionality
import logging

# Django imports for generic views and template rendering
from django.views import generic
from django.shortcuts import render
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Django imports for verifying a user is logged-in to access a view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

# Django imports for verifying a user's permissions before accessing a function
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin

# Django imports for forms
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

# Django Q imports for task management
from django_q.tasks import async_task, result

# Import for references to Django's settings.py
from django.conf import settings

# Import the catalog application's models
from django.db.models import Q
from django.urls import reverse
from catalog.forms import CheckoutForm, DomainCreateForm
from catalog.models import Domain, HealthStatus, DomainStatus, WhoisStatus, Client, History, User

# Import the Django-Q models
from django_q.models import Success, Task

# Import Python libraries for various things
import csv
import codecs
import datetime
from io import StringIO
from io import TextIOWrapper


# Setup logger
logger = logging.getLogger(__name__)


##################
# View Functions #
##################

def index(request):
    """View function for the home page, index.html."""
    # Generate counts of some of the main objects
    num_domains = Domain.objects.all().count()
    # Get counts of domains for each status
    num_domains_burned = Domain.objects.filter(domain_status__domain_status='Burned').count()
    num_domains_reserved = Domain.objects.filter(domain_status__domain_status='Reserved').count()
    num_domains_available = Domain.objects.filter(domain_status__domain_status='Available').count()
    num_domains_unavailable = Domain.objects.filter(domain_status__domain_status='Unavailable').count()
    # If the user is authenticated, get the number of checked-out domains
    if request.user.is_authenticated:
        num_domains_out = History.objects.filter(operator=request.user,
                                                 domain__domain_status__domain_status='Unavailable',
                                                 end_date__gte=datetime.datetime.now()).count()
    else:
        num_domains_out = None
    # Prepare the context for index.html
    context = {
                'num_domains': num_domains,
                'num_domains_out': num_domains_out,
                'num_domains_burned': num_domains_burned,
                'num_domains_reserved': num_domains_reserved,
                'num_domains_available': num_domains_available,
                'num_domains_unavailable': num_domains_unavailable,
               }
    # Render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context=context)

def error(request, error):
    """View function for the error page, error.html. The error message passed to this view will
    be displayed on error.html.
    """
    # Prepare the context for the error page
    context = {
                'error_message': error,
              }
    # Generate counts of some of the main objects
    return render(request, 'catalog/error.html', context=context)

@login_required
def profile(request):
    """View function for the user profile, profile.html."""
    # Get the current user's user object
    user = request.user
    # Look-up the username in the database
    current_user = User.objects.get(username=user.username)
    # Pass the results to the template
    return render(request, 'catalog/profile.html', {'current_user': current_user})

@login_required
def checkout(request, pk):
    """View function for domain checkout. The Primary Key passed to this view is used to look-up
    the requested domain.
    """
    # Fetch the domain for the provided primary key
    domain_instance = get_object_or_404(Domain, pk=pk)
    # If this is a POST request then process the form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request (binding):
        form = CheckoutForm(request.POST)
        # Check if the form is valid
        if form.is_valid():
            # Check if client exists and create it if not
            # TODO:
            # Change this to tie into a client manager
            # In the future this will be a dropdown or typeahead field
            client_name = form.cleaned_data['client']
            client = Client.objects.get(name__iexact=client_name)
            if not client:
                client_instance = Client(name=client_name)
                client_instance.save()
                client = Client.objects.get(name__iexact=client_name)
            # Process the data in form.cleaned_data as required
            history_instance = History(start_date=form.cleaned_data['start_date'],
                                       end_date=form.cleaned_data['end_date'],
                                       activity_type=form.cleaned_data['activity'],
                                       project_type=form.cleaned_data['project_type'],
                                       note=form.cleaned_data['note'],
                                       client=client,
                                       operator=request.user,
                                       domain=Domain.objects.get(pk=pk))
            # Commit the new project history
            history_instance.save()
            # Update the domain status and commit it
            domain_instance.domain_status = DomainStatus.objects.get(domain_status='Unavailable')
            domain_instance.last_used_by = request.user
            domain_instance.save()
            # Redirect to the user's checked-out domains
            return HttpResponseRedirect(reverse('my-domains'))
    # If this is a GET (or any other method) create the default form
    else:
        form = CheckoutForm(request.POST)
    # Prepare the context for the checkout form
    context = {
                'form': form,
                'domain_instance': domain_instance,
                'domain_name': domain_instance.name
               }
    # Render the checkout form page
    return render(request, 'catalog/checkout.html', context)

@login_required
def release(request, pk):
    """View function for releasing a domain back to the pool. The Primary Key passed to this view is used to look-up
    the requested domain.
    """
    # Fetch the domain for the provided primary key
    domain_instance = get_object_or_404(Domain, pk=pk)
    # If this is a GET request then check if domain can be released
    if request.method == 'GET':
        # Allow the action if the current user is the one who checked out the domain
        if request.user == domain_instance.last_used_by:
            # Reset domain status to `Available` and commit the change
            domain_instance.domain_status = DomainStatus.objects.get(domain_status='Available')
            domain_instance.save()
            # Redirect to the user's checked-out domains
            return HttpResponseRedirect(reverse('my-domains'))
        # Otherwise return an error message via error.html
        else:
            context = {
                        'error_message': 'Your user account does match the user that has checked out this domain, so you are not authorized to release it.'
                      } 
            return render(request, 'catalog/error.html', context)
    # If this is a POST (or any other method) redirect
    else:
        return HttpResponseRedirect(reverse('my-domains'))

@login_required
def upload_csv(request):
    """View function for uploading and processing csv files and importing domain names."""
    # If the request is 'GET' return the upload page
    if request.method == 'GET':
        return render(request, 'catalog/upload_csv.html')
    # If not a GET, then proceed
    try:
        # Get the `csv_file` from the POSTed form data
        csv_file = request.FILES['csv_file']
        # Do a lame/basic check to see if this is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return HttpResponseRedirect(reverse('upload_csv'))
        # The file is loaded into memory, so this view must be aware of system limits
        if csv_file.multiple_chunks():
            messages.error(request, 'Uploaded file is too big (%.2f MB).' % (csv_file.size/(1000*1000),))
            return HttpResponseRedirect(reverse('upload_csv'))
    except Exception as e:
        logging.getLogger('error_logger').error('Unable to upload/read file. ' + repr(e))
        messages.error(request, 'Unable to upload/read file: ' + repr(e))
    # Loop over the lines and save the domains to the Domains model
    try:
        # Try to read the file data
        csv_file_wrapper = StringIO(csv_file.read().decode())
        csv_reader = csv.DictReader(csv_file_wrapper, delimiter=',')
    except Exception as e:
        logging.getLogger('error_logger').error('Unable to parse file. ' + repr(e))
        messages.error(request, 'Unable to parse file: ' + repr(e))
        return HttpResponseRedirect(reverse('upload_csv'))
    try:
        # Process each csv row and commit it to the database
        for entry in csv_reader:
            logging.getLogger('error_logger').info("Adding %s to the database", entry['name'])
            # Try to format dates into the format Django expects them, YYYY-MM-DD
            # This just catches the other common format, MM-DD-YYYY
            # Other date formats will be missed and the user will see an error message after it fails to commit
            try:
                entry['creation'] = datetime.datetime.strptime(entry['creation'], '%m-%d-%Y').strftime('%Y-%m-%d')
            except:
                pass
            try:
                entry['expiration'] = datetime.datetime.strptime(entry['expiration'], '%m-%d-%Y').strftime('%Y-%m-%d')
            except:
                pass
            # Try to resolve the user-defined health_status value or default to `Healthy`
            try:
                health_status = HealthStatus.objects.get(health_status__iexact=entry['domain_status'])
            except:
                health_status = HealthStatus.objects.get(health_status='Healthy')
            entry['health_status'] = health_status
            # Try to resolve the user-defined whois_status value or default to `Enabled` as it usually is
            try:
                whois_status = WhoisStatus.objects.get(whois_status__iexact=entry['whois_status'])
            except:
                whois_status = WhoisStatus.objects.get(whois_status='Enabled')
            entry['whois_status'] = whois_status
            # Check if the optional note field is in the csv and add it as NULL if not
            if not 'note' in entry:
                entry['note'] = None
            # Check if the domain_status Foreign Key is in the csv and try to resolve the status
            if 'domain_status' in entry:
                try:
                    domain_status = DomainStatus.objects.get(domain_status__iexact=entry['domain_status'])
                except:
                    domain_status = DomainStatus.objects.get(domain_status='Available')
                entry['domain_status'] = domain_status
            else:
                domain_status = DomainStatus.objects.get(domain_status='Available')
                entry['domain_status'] = domain_status
            # The last_used_by field will only be set by Shepherd at domain check-out
            if 'last_used_by' in entry:
                entry['last_used_by'] = None
            else:
                entry['last_used_by'] = None
            # Try to pass the dict object to the Domain model
            try:
                new_domain = Domain(**entry)
                new_domain.save()
            # If there is an error, store as string and then display
            except Exception as e:
                logging.getLogger('error_logger').error(repr(e))
                messages.error(request, 'Issue processing data for ' + repr(entry['name']) + ': ' + repr(e))
                return HttpResponseRedirect(reverse('upload_csv'))
    except Exception as e:
        logging.getLogger('error_logger').error('Unable to read rows: ' + repr(e))
        messages.error(request, 'Unable to read rows: ' + repr(e))
    return HttpResponseRedirect(reverse('upload_csv'))

@login_required
def update(request):
    """View function to display the control panel for updating domain information."""
    # Check if the request is a POST and proceed with the task
    if request.method == 'POST':
        # Add an async task grouped as `Domain Updates`
        task_id = async_task('tasks.check_domains', group='Domain Updates', hook='tasks.send_slack_complete_msg')
        # Return to the update.html page with the confirmation message
        messages.success(request, 'Task ID {} has been successfully queued!'.format(task_id))
        return HttpResponseRedirect(reverse('update'))
    else:
        # Collect data for rendering the page
        total_domains = Domain.objects.all().count()
        try:
            sleep_time = settings.DOMAINCHECK_CONFIG['sleep_time']
            update_time = round(total_domains * sleep_time / 60, 2)
        except:
            sleep_time = 20
            update_time = round(total_domains * sleep_time / 60, 2)
        try:
            # Get the latest completed task from `Domain Updates`
            queryset = Task.objects.filter(group='Domain Updates')[0]
            # Get the task's start date and time
            last_update_requested = queryset.started
            # Get the task's completed time
            last_result = queryset.result
            # Check if the task was flagged as successful or failed
            if queryset.success:
                last_update_completed = queryset.stopped
                last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                last_update_completed = 'Failed'
                last_update_time = ''
        except:
            last_update_requested = 'Never Successfully Run'
            last_update_completed = ''
            last_update_time = ''
            last_result = ''
        context = {
                    'total_domains': total_domains,
                    'update_time': update_time,
                    'last_update_requested': last_update_requested,
                    'last_update_completed': last_update_completed,
                    'last_update_time': last_update_time,
                    'last_result': last_result,
                    'sleep_time': sleep_time
                }
        return render(request, 'catalog/update.html', context=context)

@login_required
def update_dns(request):
    """View function to display the control panel for updating domain DNS records."""
    # Check if the request is a POST and proceed with the task
    if request.method == 'POST':
        # Add an async task grouped as `DNS Updates`
        task_id = async_task('tasks.update_dns', group='DNS Updates', hook='tasks.send_slack_complete_msg')
        # Return to the update.html page with the success message
        messages.success(request, 'Task ID {} has been successfully queued!'.format(task_id))
        return HttpResponseRedirect(reverse('update_dns'))
    else:
        # Collect data for rendering the page
        try: 
            queryset = Task.objects.filter(group='DNS Updates')[0]
            last_update_requested = queryset.started
            last_result = queryset.result
            if queryset.success:
                last_update_completed = queryset.stopped
                last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                last_update_completed = 'Failed'
                last_update_time = ''
        except:
            last_update_requested = 'Never Successfully Run'
            last_update_completed = ''
            last_update_time = ''
            last_result = ''
        context = {
                    'last_update_requested': last_update_requested,
                    'last_update_completed': last_update_completed,
                    'last_update_time': last_update_time,
                    'last_result': last_result
                }
        return render(request, 'catalog/update_dns.html', context=context)

@login_required
def management(request):
    """View function to display the current settings configured for Shepherd."""
    # Get the DOMAINCHECK_CONFIG dictionary from settings.py
    if settings.DOMAINCHECK_CONFIG:
        config = settings.DOMAINCHECK_CONFIG
    # Pass the relevant settings to management.html
    context = {
                'virustotal_api_key': config['virustotal_api_key'],
                'sleep_time': config['sleep_time']
              }
    return render(request, 'catalog/management.html', context=context)

################
# View Classes #
################

class DomainListView(LoginRequiredMixin, generic.ListView):
    """View showing all registered domains. This view defaults to the domain_list.html template."""
    model = Domain
    paginate_by = 25

    def get_queryset(self):
        """Customize the queryset based on search."""
        # Check if a search parameter is in the request
        try:
            search_term = order_by = self.request.GET.get('domain_search')
        except:
            search_term = ''
        # If there is a search term, filter the query by domain name or category
        # TODO: We might consider using keywords like `category:technology` to search different fields
        if search_term:
            queryset = super(DomainListView, self).get_queryset()
            return queryset.filter(Q(name__icontains=search_term) | Q(all_cat__icontains=search_term)).order_by('name')
        else:
            return Domain.objects.all().order_by('domain_status')


class AvailDomainListView(LoginRequiredMixin, generic.ListView):
    """View showing only available domains. This view calls the available_domains.html template."""
    model = Domain
    queryset = Domain.objects.filter(domain_status__domain_status='Available').order_by('name')
    template_name = 'catalog/available_domains.html'
    paginate_by = 25


class ActiveDomainListView(LoginRequiredMixin, generic.ListView):
    """View showing only available domains. This view calls the active_domains.html template."""
    model = Domain
    queryset = Domain.objects.filter(domain_status__domain_status='Unavailable').order_by('name')
    template_name = 'catalog/active_domains.html'
    paginate_by = 25


class ResDomainListView(LoginRequiredMixin, generic.ListView):
    """View showing only reserved domains. This view calls the reserved_domains.html template."""
    model = Domain
    queryset = Domain.objects.filter(domain_status__domain_status='Reserved').order_by('name')
    template_name = 'catalog/reserved_domains.html'
    paginate_by = 25


class GraveyardListView(LoginRequiredMixin, generic.ListView):
    """View showing only burned and retired domains. This view calls the graveyard.html template."""
    model = Domain
    queryset = Domain.objects.filter(domain_status__domain_status='Burned')
    template_name = 'catalog/graveyard.html'
    paginate_by = 25


class DomainDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified domain. This view defaults to the domain_detail.html
    template.
    """
    model = Domain


class ActiveDomainsByUserListView(LoginRequiredMixin, generic.ListView):
    """View showing only the domains checked-out by the current user. This view calls the
    active_domains_user.html template.
    """
    model = History
    template_name = 'catalog/active_domains_user.html'
    paginate_by = 25

    def get_queryset(self):
        """Modify this built-in function to filter results from the History by the current user."""
        # Only return project entries for the current user where the current domain status is `Unavailable`
        return History.objects.filter(operator=self.request.user,
                                      domain__domain_status__domain_status='Unavailable',
                                      end_date__gte=datetime.datetime.now()).order_by('end_date')


class HistoryCreate(LoginRequiredMixin, CreateView):
    """View for creating new project history entries. This view defaults to the
    history_form.html template.
    """
    model = History
    fields = '__all__'
    success_url = reverse_lazy('domains')

    def get_initial(self):
        """Set the initial values for the form."""
        domain = get_object_or_404(Domain, pk=self.kwargs.get('pk'))
        return {
                'domain': domain,
               }


class HistoryUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing project history entries. This view defaults to the
    history_form.html template.
    """
    model = History
    fields = ['client', 'activity_type', 'project_type', 'end_date', 'note', 'operator']
    success_url = reverse_lazy('domains')


class HistoryDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing project history entries. This view defaults to the
    history_confirm_delete.html template.
    """
    model = History
    success_url = reverse_lazy('domains')


class DomainCreate(LoginRequiredMixin, CreateView):
    """View for creating new domain name entries. This view defaults to the
    domain_form.html template.
    """
    model = Domain
    form_class = DomainCreateForm
    success_url = reverse_lazy('domains')


class DomainUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing domain name entries. This view defaults to the
    history_form.html template.
    """
    model = Domain
    fields = '__all__'
    success_url = reverse_lazy('domains')


class DomainDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing domain name entries.his view defaults to the
    domain_confirm_delete.html template.
    """
    model = Domain
    success_url = reverse_lazy('domains')
