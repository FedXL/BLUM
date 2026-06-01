from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import whatsapp_helper.whatsapp as wa
import json

@csrf_exempt
def whatsapp_hook(request):
    if request.method != 'POST':
        return HttpResponse("Use POST request", status=400)
    payload = json.loads(request.body)
    if "method" not in payload:
        return HttpResponse("Include 'method' in request", status=400)
    
    method = payload['method']
    result = {}
    try:
        if method == 'send_message':
            result['result'] = wa.send_message(**payload)
        elif method == 'send_template':
            result['result'] = wa.send_template(**payload)
        elif method == 'batch_send_template':
            result['result'] = wa.batch_send_template(**payload)
        else:
            result['result'] = "Unknown method"
            return HttpResponse(json.dumps(result), status=400)
        return HttpResponse(json.dumps(result))
    except Exception as e:
        result['result'] = "Request caused exception " + repr(e)
        return HttpResponse(json.dumps(result), status=400)

