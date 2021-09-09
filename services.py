import http.client
import json
from datetime import datetime, timezone


def get_normalized_nodes(curie_list):
    json_data = json.dumps({'curies': curie_list, 'conflate': False})
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    conn = http.client.HTTPSConnection(host='nodenormalization-sri.renci.org')
    conn.request('POST', '/1.1/get_normalized_nodes', body=json_data, headers=headers)
    response = conn.getresponse()
    if response.status == 200:
        return json.loads(response.read())
    return {}


def log_timestamp(text):
    file_suffix_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S%f")
    print(f"{file_suffix_timestamp}: {text}")
