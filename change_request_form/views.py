import logging

from django.views.generic.edit import FormView
from django.views.generic.base import TemplateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from .forms import ChangeRequestForm
from authbroker_client.client import authbroker_login_required, get_profile


logger = logging.getLogger(__file__)


@method_decorator(authbroker_login_required, name="dispatch")
class ChangeRequestFormView(FormView):
    template_name = 'change_request.html'
    form_class = ChangeRequestForm
    success_url = reverse_lazy('success')

    def get_initial(self):
        initial = super().get_initial()

        try:
            profile = get_profile(self.request)

            initial['email'] = profile['email']
            initial['name'] = profile['first_name'] + ' ' + profile['last_name']
        except Exception:
            logger.exception('Cannot get user profile')

        return initial

    def form_valid(self, form):
        self.request._ticket_id = form.create_zendesk_ticket()
        return super().form_valid(form)

    def get_success_url(self):
        url = super().get_success_url()

        return f'{url}?issue={self.request._ticket_id}'


@method_decorator(authbroker_login_required, name="dispatch")
class ChangeRequestFormSuccessView(TemplateView):
    template_name = 'change_request_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.request.GET.get('issue', 'Not specified')
        return context
