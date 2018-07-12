from django.views.generic.edit import FormView

from .forms import ChangeRequestForm


class ChangeRequestFormView(FormView):
    template_name = 'change_request.html'
    form_class = ChangeRequestForm
    success_url = '/success/'
