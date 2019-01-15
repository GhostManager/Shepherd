"""This contains tasks to be run using Django Q and Redis."""

# Import the catalog application's models and settings
from django.conf import settings
from catalog.models import Domain, History, DomainStatus, HealthStatus

# Import custom modules
from modules.review import DomainReview
from modules.dns import DNSCollector

# Import Python libraries for various things
import json
import requests
import datetime
from datetime import date


def send_slack_msg(message):
    """Accepts message text and sends it to Slack. This requires Slack settings and a webhook be
    configured in the application's settings.

    Parameters:

    message         A string to be sent as the Slack message
    """
    try:
        enable_slack = settings.SLACK_CONFIG['enable_slack']
    except:
        enable_slack = False
    if enable_slack:
        try:
            slack_emoji = settings.SLACK_CONFIG['slack_emoji']
            slack_username = settings.SLACK_CONFIG['slack_username']
            slack_webhook_url = settings.SLACK_CONFIG['slack_webhook_url']
            slack_alert_target = settings.SLACK_CONFIG['slack_alert_target']
            slack_channel = settings.SLACK_CONFIG['slack_channel']
            slack_capable = True
        except Exception as error:
            slack_capable = False

        if slack_capable:
            message = slack_alert_target + ' ' + message
            slack_data = {
                        'username': slack_username, 
                        'icon_emoji': slack_emoji, 
                        'channel': slack_channel, 
                        'text': message
                        }
            response = requests.post(slack_webhook_url, data=json.dumps(slack_data), headers={'Content-Type':'application/json'})
            if response.status_code != 200:
                print('[!] Request to slack returned an error %s, the response is:\n%s' % (response.status_code, response.text))

def send_slack_complete_msg(task):
    """Function to send a Slack message for a task. Meant to be used as a hook for an async_task()."""
    if task.success:
        send_slack_msg('Task {} has completed its run. It completed successfully with no additional result data.'.format(task.name))
    else:
        if task.result:
            send_slack_msg('Task {} failed with this result: {}'.format(task.name, task.result))
        else:
            send_slack_msg('Task {} failed with no result/error data. Check the Django Q admin panel.'.format(task.name))

def release_domains(no_action=False):
    """Pull all domains currently checked-out in Shepherd and update the status to Available if the
    project's end date is today or in the past.

    Parameters:

    no_action       Defaults to False. Set to True to take no action and just return a list
                    of domains that should be released now.
    """
    domains_to_be_released = []
    # First get all domains set to `Unavailable`
    queryset = Domain.objects.filter(domain_status__domain_status='Unavailable')
    # Go through each `Unavailable` domain and check it against projects
    for domain in queryset:
        # Get all projects for the domain
        project_queryset = History.objects.filter(domain__name=domain.name)
        release_me = True
        # Check each project's end date to determine if all are in the past or not
        for project in project_queryset:
            if date.today() < project.end_date:
                release_me = False
        # If release_me is still true, release the domain
        if release_me:
            domains_to_be_released.append(domain)
    # Check no_action and just return list if it is set to True
    if no_action:
        return domains_to_be_released
    else:
        for domain in domains_to_be_released:
            print('Releasing {} back into the pool.'.format(domain.name))
            domain_instance = Domain.objects.get(name=domain.name)
            domain_instance.domain_status = DomainStatus.objects.get(domain_status='Available')
            domain_instance.save()
        return domains_to_be_released

def check_domains():
    """Initiate a check of all domains in the Domain model and update each domain status."""
    # Get all domains from the database
    domain_queryset = Domain.objects.all()
    domain_review = DomainReview(domain_queryset)
    lab_results = domain_review.check_domain_status()
    for domain in lab_results:
        try:
            # The `domain` is already a Domain object so this query might be unnecessary :thinking_emoji:
            domain_instance = Domain.objects.get(name=domain.name)
            # Flip status if a domain has been flagged as burned
            if lab_results[domain]['burned']:
                domain_instance.health_status = HealthStatus.objects.get(health_status='Burned')
                domain_instance.domain_status = DomainStatus.objects.get(domain_status='Burned')
                message = '*{}* has been flagged as burned because: {}'.format(domain.name, lab_results[domain]['burned_explanation'])
                if lab_results[domain]['categories']['bad']:
                    message = message + ' (Bad categories: {})'.format(lab_results[domain]['categories']['bad'])
                send_slack_msg(message)
            # Update other fields for the domain object
            domain_instance.health_dns = lab_results[domain]['health_dns']
            domain_instance.burned_explanation = lab_results[domain]['burned_explanation']
            domain_instance.all_cat = lab_results[domain]['categories']['all']
            domain_instance.talos_cat = lab_results[domain]['categories']['talos']
            domain_instance.opendns_cat = lab_results[domain]['categories']['opendns']
            domain_instance.bluecoat_cat = lab_results[domain]['categories']['bluecoat']
            domain_instance.ibm_xforce_cat = lab_results[domain]['categories']['xforce']
            domain_instance.trendmicro_cat = lab_results[domain]['categories']['trendmicro']
            domain_instance.fortiguard_cat = lab_results[domain]['categories']['fortiguard']
            domain_instance.mx_toolbox_status = lab_results[domain]['categories']['mxtoolbox']
            domain_instance.save()
        except Exception as error:
            print('[!] Error updating "{}". Error: {}'.format(domain.name, error))
            pass

def update_dns():
    """Initiate a check of all domains in the Domain model and update each domain's DNS records."""
    dns_toolkit = DNSCollector()
    # Get all domains from the database
    domain_queryset = Domain.objects.all()
    for domain in domain_queryset:
        # Get each type of DNS record for the domain
        try:
            try:
                temp = []
                ns_records_list = dns_toolkit.get_dns_record(domain.name, 'NS')
                for rdata in ns_records_list.response.answer:
                    for item in rdata.items:
                        temp.append(item.to_text())
                ns_records = ', '.join(x.strip('.') for x in temp)
            except:
                ns_records = 'None'
            try:
                temp = []
                a_records = dns_toolkit.get_dns_record(domain.name, 'A')
                for rdata in a_records.response.answer:
                    for item in rdata.items:
                        temp.append(item.to_text())
                a_records = ', '.join(temp)
            except:
                a_records = None
            try:
                mx_records = dns_toolkit.return_dns_record_list(domain.name, 'MX')
            except:
                mx_records = None
            try:
                txt_records = dns_toolkit.return_dns_record_list(domain.name, 'TXT')
            except:
                txt_records = None
            try:
                soa_records = dns_toolkit.return_dns_record_list(domain.name, 'SOA')
            except:
                soa_records = None
            try:
                dmarc_record = dns_toolkit.return_dns_record_list('_dmarc.' + domain.name, 'TXT')
            except:
                dmarc_record = None
            # Assemble the string to be stored in the database
            dns_records_string = ''
            if ns_records:
                dns_records_string += 'NS: %s ::: ' % ns_records
            if a_records:
                dns_records_string += 'A: %s ::: ' % a_records
            if mx_records:
                dns_records_string += 'MX: %s ::: ' % mx_records
                if dmarc_record:
                    dns_records_string += 'DMARC: %s ::: ' % dmarc_record
                else:
                    dns_records_string += 'DMARC: MX configured without a DMARC record! ::: '
            if txt_records:
                dns_records_string += 'TXT: %s ::: ' % txt_records
            if soa_records:
                dns_records_string += 'SOA: %s ::: ' % soa_records
        except:
            dns_records_string = 'None'
        # Look-up the individual domain and save the new record string for that domain
        domain_instance = Domain.objects.get(name=domain.name)
        domain_instance.dns_record = dns_records_string
        domain_instance.save()

