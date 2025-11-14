import json


def hello_http(request):
    """HTTP Cloud Function entry point for Gen2 (Python 3.11).
    Returns a simple JSON hello world payload.
    """
    payload = {"message": "Hello, World!"}
    return (json.dumps(payload), 200, {"Content-Type": "application/json"})



