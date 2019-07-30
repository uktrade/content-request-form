from django.urls import path, include

from change_request_form.views import ChangeRequestFormView, ChangeRequestFormSuccessView
from core.views import healthcheck

urlpatterns = [
    path('', ChangeRequestFormView.as_view(), name='home'),
    path('success/', ChangeRequestFormSuccessView.as_view(), name='success'),
    path('auth/', include('authbroker_client.urls')),
    path('check/', healthcheck, name='healthcheck')
]
