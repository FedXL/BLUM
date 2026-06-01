from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import misc.terra_motors as tm
import misc.china_delivery as cd
import json

@csrf_exempt
def misc_handler(request):
    if request.method != 'POST':
        return HttpResponse("Use POST request", status=400)
    payload = json.loads(request.body)
    if "method" not in payload:
        return HttpResponse("Include 'method' in request", status=400)
    
    method = payload['method']
    result = {}
    try:
        if method == 'terra_motors_send':
            result['result'] = tm.get_and_send(**payload)
        elif method == 'china_get_status':
            result['result'] = cd.get_status(**payload)
        elif method == 'china_check_client':
            result['result'] = cd.check_client(**payload)
        elif method == 'china_add_tracks':
            result['result'] = cd.add_tracks(**payload)
        elif method == 'china_update_table':
            result['result'] = cd.update_table(**payload)
        elif method == 'china_send_notifications':
            result['result'] = cd.send_notifications(**payload)
        else:
            result['result'] = "Unknown method"
            return HttpResponse(json.dumps(result), status=400)
        return HttpResponse(json.dumps(result))
    except Exception as e:
        result['result'] = "Request caused exception " + repr(e)
        return HttpResponse(json.dumps(result), status=400)

