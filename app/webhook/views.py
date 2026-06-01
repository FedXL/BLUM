from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from webhook.fib import fib

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        if "number" in payload:
            return HttpResponse(fib(int(payload["number"])))
        return HttpResponse("Please tell us your number!")
    return HttpResponse("POST only, my man!")