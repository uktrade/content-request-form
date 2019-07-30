from django.http import HttpResponse


def healthcheck(request):
    """An initial health check endpoint."""
    return HttpResponse('OK')
