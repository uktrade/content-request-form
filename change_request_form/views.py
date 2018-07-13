from django.views.generic.edit import FormView
from django.views.generic.base import TemplateView
from django.urls import reverse_lazy

from .forms import ChangeRequestForm


class ChangeRequestFormView(FormView):
    template_name = 'change_request.html'
    form_class = ChangeRequestForm
    success_url = reverse_lazy('success')

    def form_valid(self, form):
        self.request.JIRA_ticket_id = form.create_jira_issue()
        return super().form_valid(form)

    def get_success_url(self):
        url = super().get_success_url()

        return url + '?issue=' + self.request.JIRA_ticket_id


class ChangeRequestFormSuccessView(TemplateView):
    template_name = 'change_request_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['issue'] = self.request.GET.get('issue', 'Not specified')
        return context
