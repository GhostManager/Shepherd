"""This contains all of the forms for the catalog application."""

import datetime

from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from catalog.models import Domain, HealthStatus, DomainStatus, ActivityType, ProjectType, Client, History


class DateInput(forms.DateInput):
    input_type = 'date'


class CheckoutForm(forms.Form):
    """Form used for domain checkout. Updates the domain (status) and creates a project entry."""
    client = forms.CharField(help_text='Enter a name for the client.')
    start_date = forms.DateField(help_text='Select a start date for the project.')
    end_date = forms.DateField(help_text='Select an end  date for the project.')
    project_type = forms.ModelChoiceField(queryset=ProjectType.objects.all(), to_field_name='project_type', help_text='Select the type of project.')
    activity = forms.ModelChoiceField(queryset=ActivityType.objects.all(), to_field_name='activity', help_text='Select how this domain will be used.')
    note = forms.CharField(help_text='Enter a note, such as how this domain will be used.', widget=forms.Textarea, required=False)
    slack_channel = forms.CharField(help_text='Enter a Slack channel with the hashtag where notifications can be sent (e.g. #shepherd, with the hashtag).', required=False)

    class Meta:
        widgets = {
                    'start_date': forms.DateInput(attrs={'id': 'datepicker'}),
                    'end_date': forms.DateInput(attrs={'class': 'datepicker'})
                  }

    def clean_end_date(self):
        """Clean and sanitize user input."""
        data = self.cleaned_data['end_date']
        # Check if a date is not in the past. 
        if data < datetime.date.today():
            raise ValidationError(_('Invalid date: The provided end date is in past'))
        # Return the cleaned data.
        return data


class DomainCreateForm(forms.ModelForm):
    """Form used with the DomainCreate CreateView in models.py to allow excluding fields."""
    class Meta:
        """Metadata for the model form."""
        model = Domain
        exclude = ('last_used_by', 'burned_explanation')
        widgets = {
                    'creation': DateInput(),
                    'expiration': DateInput()
                  }
