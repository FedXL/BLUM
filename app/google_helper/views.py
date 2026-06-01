from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import google_helper.sheets as gs

def execute_method(payload):
    method = payload['method']
    if method == 'get_list':
        result = gs.get_list(**payload)
    elif method == 'append_row':
        result = gs.append_row(**payload)
    elif method == 'append_rows':
        result = gs.append_rows(**payload)
    elif method == 'find_all':
        result = gs.find_all(**payload)
    elif method == 'find':
        result = gs.find(**payload)
    elif method == 'get_unique':
        result = gs.get_unique(**payload)
    elif method == 'update_cells':
        result = gs.update_cells(**payload)
    else:
        raise ValueError("Unknown method")
    return result

@csrf_exempt
def google_hook(request):
    if request.method != 'POST':
        return HttpResponse("Use POST request", status=400)
    payload = json.loads(request.body)
    if "method" not in payload:
        return HttpResponse("Include 'method' in request", status=400)
    
    try:
        result = {}
        if payload['method'] == "multi_method":
            result['result'] = []
            for request in payload['methods']:
                result['result'].append(execute_method(request))
        else:
            result['result'] = execute_method(payload)
        return HttpResponse(json.dumps(result))
    except Exception as e:
        result['result'] = "Request caused exception " + repr(e)
        return HttpResponse(json.dumps(result), status=400)
