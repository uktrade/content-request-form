from django.urls import path, include

from change_request_form.views import ChangeRequestFormView, ChangeRequestFormSuccessView

urlpatterns = [
    path('', ChangeRequestFormView.as_view(), name='home'),
    path('success/', ChangeRequestFormSuccessView.as_view(), name='success'),
    path('auth/', include('authbroker_client.urls')),
]
