from django.shortcuts import render


def home(request):
    """
    Home page view for the Vineyard Group Fellowship API server.
    Displays API information and available endpoints.
    """
    context = {
        'server_name': 'Vineyard Group Fellowship API',
        'version': 'v1',
        'status': 'active',
    }
    return render(request, 'home.html', context)


def health_check(request):
    """
    Health check view for monitoring and status verification.
    """
    context = {
        'status': 'healthy',
        'service': 'Vineyard Group Fellowship API',
    }
    return render(request, 'health_check.html', context)
