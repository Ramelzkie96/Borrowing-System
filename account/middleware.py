# account/middleware.py
from django.http import Http404
from django.shortcuts import render
from django.utils.timezone import now


class Custom404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404:
            return render(request, '404.html', status=404)
        return response



class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Update the session with the current timestamp
            request.session['last_activity'] = now().timestamp()

        response = self.get_response(request)
        return response