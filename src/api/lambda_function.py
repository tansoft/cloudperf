import json
import data_layer

def webapi_status(requests):
    return {
        'statusCode': 200,
        'result': {
            "activeNodes": 214,
            "avgLatency": 31,
            "uptime": "97.9",
            "lastUpdate": "2025-01-04T01:53:37.308Z"
        }
    }

# ?src=US-NYC-7922,US-NYC-3356&dist=US-SFO-16509,US-SFO-15169
def webapi_performance(requests):
    return {
        'statusCode': 200,
        'result': {
            "samples": 1000,
            "avgLatency": 45,
            "medianLatency": 42,
            "p70Latency": 50,
            "timeSeriesData": [
                {"date": "2025-01-04","avgLatency": 50},
                {"date": "2025-01-03","avgLatency": 52},
                {"date": "2025-01-02","avgLatency": 48},
                {"date": "2025-01-01","avgLatency": 39},
                {"date": "2024-12-31","avgLatency": 48},
                {"date": "2024-12-30","avgLatency": 45},
                {"date": "2024-12-29","avgLatency": 51}
            ],
            "asnData": [
                {"asn": "AS7922","avgLatency": 42},
                {"asn": "AS3356","avgLatency": 48}
            ],
            "cityData": [
                {"city": "New York","avgLatency": 45},
                {"city": "San Francisco","avgLatency": 55}
            ],
            "sourceLocations": [
                {"cityId": "US-NYC-7922","asn": "7922","latitude": 45.68122565778718,"longitude": -116.72670125958872},
                {"cityId": "US-NYC-3356","asn": "3356","latitude": 45.905292481682665,"longitude": -114.04344943278507}
            ],
            "destLocations": [
                {"cityId": "US-SFO-16509","asn": "16509","latitude": 42.24565280543524,"longitude": -65.55765414750672},
                {"cityId": "US-SFO-15169","asn": "15169","latitude": 45.52876173811771,"longitude": -73.46462807876824}
            ],
            "latencyData": [
                {"sourceCityId": "US-NYC-7922","sourceAsn": "7922","sourceLat": 45.68122565778718,"sourceLon": -116.72670125958872,
                "destCityId": "US-SFO-16509","destAsn": "16509","destLat": 42.24565280543524,"destLon": -65.55765414750672,"latency": 69},
                {"sourceCityId": "US-NYC-7922","sourceAsn": "7922","sourceLat": 45.68122565778718,"sourceLon": -116.72670125958872,
                "destCityId": "US-SFO-15169","destAsn": "15169","destLat": 45.52876173811771,"destLon": -73.46462807876824,"latency": 23},
                {"sourceCityId": "US-NYC-3356","sourceAsn": "3356","sourceLat": 45.905292481682665,"sourceLon": -114.04344943278507,
                "destCityId": "US-SFO-16509","destAsn": "16509","destLat": 42.24565280543524,"destLon": -65.55765414750672,"latency": 33},
                {"sourceCityId": "US-NYC-3356","sourceAsn": "3356","sourceLat": 45.905292481682665,"sourceLon": -114.04344943278507,
                "destCityId": "US-SFO-15169","destAsn": "15169","destLat": 45.52876173811771,"destLon": -73.46462807876824,"latency": 63}
            ]
        }
    }

# country=US&city=US-NYC
def webapi_asn(requests):
    return {
        'statusCode': 200,
        'result': [
            {"id": "AS7922","name": "Comcast","cityId": "US-NYC-7922"},
            {"id": "AS3356","name": "Level 3","cityId": "US-NYC-3356"}
        ]
    }

# country=CN
def webapi_city(requests):
    return {
        'statusCode': 200,
        'result': [
            {"id": "CN-SHA","name": "Shanghai","lat": 31.2304,"lon": 121.4737},
            {"id": "CN-BEJ","name": "Beijing","lat": 39.9042,"lon": 116.4074}
        ]
    }

# get
# post {"name": "tes","cityIds": ["test"]}
# delete
def webapi_cityset(requests):
    return {
        'statusCode': 200,
        'result': [
            {"id": 1,"name": "US East Coast","cityIds": ["US-NYC-7922","US-NYC-3356"]},
            {"id": 2,"name": "US West Coast","cityIds": ["US-SFO-16509","US-SFO-15169"]},
            {"id": 3,"name": "cloudperf","cityIds": ["US-IAD-16509","US-IAD-16510"]}
        ]
    }

def webapi_ipinfo(requests):
    return {
        'statusCode': 200,
        'result': {
            "ip": "2.3.4.5",
            "asn": "AS15169",
            "country": "US",
            "region": "California",
            "asnType": "Content",
            "ipRange": [
                "2.3.4.0",
                "2.3.4.255"
            ],
            "cityId": "US-SFO-15169",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
    }

def webapi_asninfo(requests):
    return {
        'statusCode': 200,
        'result': [
            {
                "asn": "AS16509",
                "country": "US",
                "region": "Virginia",
                "asnType": "Cloud",
                "ipRange": [
                    "3.2.34.0",
                    "3.2.34.255"
                ],
                "cityId": "US-IAD-16509",
                "latitude": 38.9519,
                "longitude": -77.448
            },
            {
                "asn": "AS16510",
                "country": "US",
                "region": "Virginia",
                "asnType": "Cloud",
                "ipRange": [
                    "3.2.35.0",
                    "3.2.35.255"
                ],
                "cityId": "US-IAD-16510",
                "latitude": 36.9519,
                "longitude": -75.448
            }
        ]
    }


'''
requests: {
    version: "apigw-httpapi2.0",
    srcip: "72.21.198.64",
    useragent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    next: "qwedewf",
    method: "GET",
    body: "",
    path: "/"
}
'''
def fping_logic(requests):
    ret = {"job":[],"next":"","interval":3600,"status":200}
    if requests['method'] == 'POST':
        jobResult = json.loads(requests['body'])
    if requests['useragent'].startswith('fping-watchmen'):
        # get ping job here
        pass
    else:
        pass
    cityid = data_layer.get_cityid_by_ip(requests['srcip'])
    if cityid != 0:
        print(cityid)
    ret["job"].append({
        "jobid": "123-1",
        "command": "fping -g 8.8.8.5 8.8.8.10 -r 2 -a -q",
    })
    ret["job"].append({
        "jobid": "123-2",
        "command": "fping -g 1.1.1.0 1.1.1.3 -r 2 -a -q",
    })
    ret["job"].append({
        "jobid": "123-3",
        "command": "fping -g 110.242.68.1 110.242.68.10 -r 2 -a -q",
    })
    ret["next"] = "sfkR1xjer"
    ret["interval"] = 10
    return {
        'statusCode': 200,
        'result': ret
    }

def lambda_handler(event, context):
    print(event)
    if 'logic' in event:
        pass
    requests = {'version': '1.0'}
    if 'version' in event:
        if event['version'] == '2.0':
            requests = {
                'version': 'apigw-httpapi2.0',
                'srcip': event['requestContext']['http']['sourceIp'],
                'useragent': event['requestContext']['http']['userAgent'],
                'method': event['requestContext']['http']['method'],
                'body': event['body'] if 'body' in event else null,
                'path': event['requestContext']['http']['path']
            }
        elif event['version'] == '1.0':
            requests = {
                'version': 'apigw-httpapi1.0',
                'srcip': event['requestContext']['identity']['sourceIp'],
                'useragent': event['requestContext']['identity']['userAgent'],
                'method': event['requestContext']['httpMethod'],
                'body': event['body'],
                'path': event['requestContext']['path']
            }
    else:
        # 健康检查字段：
        # {'requestContext': {'elb': {'targetGroupArn': 'arn:aws:elasticloadbalancing:us-east-1:675857233193:targetgroup/Cloudp-cloud-Y6ZDQYYVEO72/ba784127f812d2e6'}},
        # 'httpMethod': 'GET', 'path': '/', 'queryStringParameters': {}, 'headers': {'user-agent': 'ELB-HealthChecker/2.0'}, 
        # 'body': '', 'isBase64Encoded': False}
        requests = {
            'version': 'alb',
            'srcip': event['headers']['x-forwarded-for'] if 'x-forwarded-for' in event['headers'] else '',
            'useragent': event['headers']['user-agent'],
            'method': event['httpMethod'],
            'body': event['body'],
            'path': event['path']
        }
    querys = event['queryStringParameters']
    requests['next'] = querys['next'] if 'next' in querys else ''
    print(requests)
    apimapping = {
        '/job':fping_logic,
        '/api/status': webapi_status,
        '/api/ipinfo': webapi_ipinfo,
        '/api/asninfo': webapi_asninfo,
        '/api/cityset': webapi_cityset,
        '/api/city': webapi_city,
        '/api/asn': webapi_asn,
        '/api/performance': webapi_performance,
    }
    if requests['path'] not in apimapping:
        if requests['useragent'].startswith('ELB-HealthChecker/2.0'):
            ret = {'statusCode':200, 'result':'healthly'}
        else:
            ret = {'statusCode':404, 'result':'not found'}
    else:
        ret = apimapping[requests['path']](requests)
    #ret['result']['debug'] = event;
    #ret['result']['requests'] = requests;
    if requests['version'] == 'apigw-httpapi2.0':
        return {
            'statusCode': ret['statusCode'],
            'body': json.dumps(ret['result'])
        }
    return {
        'statusCode': ret['statusCode'],
        "headers": {
            "Content-Type": "application/json"
        },
        'body': json.dumps(ret['result'])
    }

# local test
if __name__ == "__main__":
    import sys
    print(sys.argv[1])
    ret = lambda_handler(json.loads(sys.argv[1]), None)
    print(ret)