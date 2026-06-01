from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import telegram_helper.telegram as tg

@csrf_exempt
def telegram_hook(request):
    if request.method != 'POST':
        return HttpResponse("Use POST request", status=400)
    payload = json.loads(request.body)
    if "method" not in payload:
        return HttpResponse("Include 'method' in request", status=400)
    
    method = payload['method']
    result = {}
    try:
        if method == 'send_message':
            result['result'] = tg.send_message(**payload)
        elif method == 'batch_send':
            result['result'] = tg.batch_send(**payload)
        elif method == 'batch_send_unique':
            result['result'] = tg.batch_send_unique(**payload)
        else:
            result['result'] = "Unknown method"
            return HttpResponse(json.dumps(result), status=400)
        return HttpResponse(json.dumps(result))
    except Exception as e:
        result['result'] = "Request caused exception " + repr(e)
        return HttpResponse(json.dumps(result), status=400)
