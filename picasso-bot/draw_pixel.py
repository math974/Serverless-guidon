from datetime import datetime
import json

def hello_http(request):
    response_data = {
        'status': 'OK',
        'timestamp': datetime.utcnow().isoformat(),
        'Message': 'Drawing completed',
    }

    return json.dumps(response_data), 200