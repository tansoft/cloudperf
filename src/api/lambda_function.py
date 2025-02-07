import json
import settings
import data_layer
import ipaddress
from urllib.parse import unquote_plus
from itertools import chain

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

def webapi_statistics(requests):
    data = data_layer.query_statistics_data()
    return {
        'statusCode': 200,
        'result': data
    }

# //fixme，由于相同asn在同一个城市有多个asn号码，会造成选择cityid时少了，如：RU,Moscow,PJSC Rostelecom
# //fixme, city名字中有空格，貌似搜索有问题，如：DE,Frankfurt am Main 出不来16509，测试ip：63.176.70.29
# ?src=US-NYC-7922,US-NYC-3356&dist=US-SFO-16509,US-SFO-15169
def webapi_performance(requests):
    if 'src' not in requests['query'] or 'dist' not in requests['query']:
        return {'statusCode': 400, 'result': 'param src and dist not found!'}
    src = unquote_plus(requests['query']['src'])
    dist = unquote_plus(requests['query']['dist'])
    latencyData = data_layer.get_latency_data_cross_city(src, dist)
    rawData = data_layer.get_latency_rawdata_cross_city(src, dist)
    # print(latencyData)
    # src,dist,samples,min,max,avg,p50,p70,p90,p95
    # "1395638387,2228836286,10,23900,25500,24600.0000,24600.0000,24800.0000,25100.0000,25100.0000",
    if latencyData == None or rawData == None:
        return {'statusCode': 400, 'result': 'param src and dist invalid!'}
    srclist = src.split(',')
    distlist = dist.split(',')
    outdata = {
        "samples": 0,
        "srcCityIds": len(srclist),
        "distCityIds": len(distlist),
        "asnData": [],
        "cityData": [],
        "latencyData": [],
        "rawData": [],
    }
    # 找到所有相关的city_id对应对象
    cityobjs = {}
    for city_id in chain(srclist, distlist):
        city_id = int(city_id)
        city_obj = data_layer.get_cityobject_by_id(city_id)
        print(city_id, city_obj)
        if city_obj and len(city_obj) > 0:
            cityobjs[city_id] = city_obj[0]
    data = {
        'asn': {},
        'city': {}
    }
    for item in latencyData:
        # samples数据汇总
        outdata['samples'] += item['samples']
        # 各种Latency数据汇总
        for key in ('min','max','avg','p50','p70','p90','p95'):
            if key not in outdata:
                outdata[key] = {'samples':0, 'data':0}
            outdata[key]['samples'] += item['samples']
            outdata[key]['data'] += item[key] * item['samples']
        if item['src'] in cityobjs and item['dist'] in cityobjs:
            srcobj = cityobjs[item['src']]
            distobj = cityobjs[item['dist']]
            # 分cityid的延迟数据分列，取p70
            outdata['latencyData'].append({
                'srcCity': data_layer.friendly_cityname(srcobj),
                'srcAsn': data_layer.friendly_cityshortasn(srcobj),
                'srcLat': srcobj['latitude'],
                'srcLon': srcobj['longitude'],
                'destCity': data_layer.friendly_cityname(distobj),
                'destAsn': data_layer.friendly_cityshortasn(distobj),
                'destLat': distobj['latitude'],
                'destLon': distobj['longitude'],
                'latency': round(item['p70']/1000, 1)
            })
            # 分asn/city的延迟数据汇总，取p70
            for key in ('asn','city'):
                if key == 'asn':
                    srcsubkey = 'ASN' + str(srcobj['asn']) + ' ' + srcobj['name']
                    distsubkey = 'ASN' + str(distobj['asn']) + ' ' + distobj['name']
                else:
                    srcsubkey = srcobj['name']
                    distsubkey = distobj['name']
                for subkey in (srcsubkey,distsubkey):
                    if subkey not in data[key]:
                        data[key][subkey] = {'samples':0, 'data':0}
                    data[key][subkey]['samples'] += item['samples']
                    data[key][subkey]['data'] += item['p70'] * item['samples']

    # 各种Latency数据汇总
    outdata['samples'] = int(outdata['samples'])
    for key in ('min','max','avg','p50','p70','p90','p95'):
        if key in outdata:
            outdata[key] = round(outdata[key]['data'] / outdata[key]['samples'] / 1000, 1)
        else:
            outdata[key] = 0

    # 分asn/city的延迟数据汇总，取p70
    print(data)
    for key in ('asn','city'):
        for k, v in data[key].items():
            outdata[key+'Data'].append({
                key: k,
                'p70': round(data[key][k]['data'] / data[key][k]['samples'] / 1000, 1)
            })

    # 原始数据处理
    for item in rawData:
        if item['src'] in cityobjs and item['dist'] in cityobjs:
            srcobj = cityobjs[item['src']]
            distobj = cityobjs[item['dist']]
            outdata['rawData'].append({
                'srcCity': data_layer.friendly_cityname(srcobj) + " - " + str(item['src']),
                'srcAsn': data_layer.friendly_cityasn(srcobj),
                'srcIP': f"{srcobj['startIp']} - {srcobj['endIp']}",
                'destCity': data_layer.friendly_cityname(distobj) + " - " + str(item['dist']),
                'destAsn': data_layer.friendly_cityasn(distobj),
                'destIP': f"{distobj['startIp']} - {distobj['endIp']}",
                'samples': int(item['samples']),
                'min': round(item['min']/1000, 2),
                'max': round(item['max']/1000, 2),
                'avg': round(item['avg']/1000, 2),
                'p50': round(item['p50']/1000, 2),
                'p70': round(item['p70']/1000, 2),
                'p90': round(item['p90']/1000, 2),
                'p95': round(item['p95']/1000, 2),
                'time': item['update_time'].timestamp()
            })

    return {
        'statusCode': 200,
        'result': outdata
    }

# {username: "admin", password: "admin"}
def webapi_login(requests):
    data = json.loads(requests['body'])
    if 'username' in data and 'password' in data:
        ret = data_layer.validate_user(data['username'], data['password'])
        if ret != None:
            return {
                'statusCode': 200,
                'result': ret
            }
    return {
        'statusCode': 403,
        'result': "username or password error!"
    }

def webapi_updateuser(requests):
    obj = json.loads(requests['body'])
    return data_layer.create_user(obj['username'], obj['password'], obj['role'])

def webapi_changepasswd(requests):
    obj = json.loads(requests['body'])
    userobj = data_layer.get_user_info_by_cookie(requests['cookie'])
    if userobj:
        return data_layer.create_user(userobj['user'], obj['password'], userobj['auth'])
    return {
        'statusCode': 403,
        'result': "username or password error!"
    }

# country=US&city=US-NYC
def webapi_asn(requests):
    cityset = 0
    if 'cityset' in requests['query']:
        cityset = int(requests['query']['cityset'])
    asns = []
    if 'country' in requests['query'] and len(requests['query']['country']) >= 2:
        if 'city' in requests['query'] and len(requests['query']['city']) >= 2:
            asns = data_layer.get_asns_by_country_city(requests['query']['country'], unquote_plus(requests['query']['city']), cityset)
    return {
        'statusCode': 200,
        'result': asns
    }

def webapi_country(requests):
    cityset = 0
    if 'cityset' in requests['query']:
        cityset = int(requests['query']['cityset'])
    countrys = data_layer.get_countrys(cityset)
    return {
        'statusCode': 200,
        'result': countrys
    }

# country=CN
def webapi_city(requests):
    result = []
    cityset = 0
    if 'cityset' in requests['query']:
        cityset = int(requests['query']['cityset'])
    if 'country' in requests['query'] and len(requests['query']['country']) >= 2:
        result = data_layer.get_citys_by_country_code(requests['query']['country'], cityset)
    return {
        'statusCode': 200,
        'result': result
    }

# get
# post {name: "aws_temp", cityIds: ["1395638387", "1494300631", "2690672425", "2957825709"]}
# put {id: 1, name: "US East Coast1", cityIds: ["US-NYC-7922", "US-NYC-3356"]}
# delete /api/cityset?id=2
# return [{"id": 1,"name": "US","cityIds": ["1494300631", "2690672425"]},{"id": 2,"name": "USA","cityIds": ["2957825709", "2690672425"]}]
def webapi_cityset(requests):
    ret = []
    if requests['method'] == 'GET':
        ret = data_layer.get_citysets()
        ret = [
            {**item, 'cityIds': item['cityIds'].split(',') if item.get('cityIds') else []}
            for item in ret
        ]
    elif not data_layer.validate_user_cookies(settings.AUTH_ADMIN, requests['cookie']):
        return {'statusCode':403, 'result':'forbidden'}
    if requests['method'] == 'POST':
        data = json.loads(requests['body'])
        ret = data_layer.add_cityset(data['name'], map(str, data['cityIds']))
    elif requests['method'] == 'PUT':
        data = json.loads(requests['body'])
        ret = data_layer.edit_cityset(int(data['id']), data['name'], map(str, data['cityIds']))
    elif requests['method'] == 'DELETE':
        ret = data_layer.del_cityset(int(requests['query']['id']))
    return {
        'statusCode': 200,
        'result': ret
    }

def webapi_runsql(requests):
    sql = json.loads(requests['body'])
    ret = data_layer.mysql_batch_execute(sql['sql'])
    return {
        "statusCode": 200,
        "result": ret
    }

# GET /api/redis?key=test
# PUT /api/redis {key: "get", value: "val2"}
# DELETE /api/redis?key=test
def webapi_redis(requests):
    if requests['method'] == 'PUT':
        data = json.loads(requests['body'])
        data_layer.cache_set(data['key'], data['value'])
        return {
            'statusCode': 200,
            'result': data['value']
        }
    elif requests['method'] == 'GET':
        if 'key' in requests['query']:
            value = data_layer.cache_dump(requests['query']['key'])
            return {
                'statusCode': 200,
                'result': value
            }
    elif requests['method'] == 'DELETE':
        if 'key' in requests['query']:
            data_layer.cache_delete(requests['query']['key'])
            return {
                'statusCode': 200,
                'result': "ok"
            }
    return {
        'statusCode': 400,
        'result': "not support method."
    }

# ip=136.227.141.146 2296614290
def webapi_ipinfo(requests):
    if 'ip' not in requests['query']:
        return {'statusCode': 400, 'result':'need param ip.'}
    city = data_layer.get_cityobject_by_ip(requests['query']['ip'])
    if len(city) == 0:
        return {'statusCode': 404, 'result':'not found.'}
    print(city)
    return {
        "statusCode": 200,
        "result": city[0]
    }

# filter=amazon
def webapi_asninfo(requests):
    if 'filter' not in requests['query']:
        return {'statusCode': 400, 'result':'need param filter.'}
    filter = requests['query']['filter']
    if len(filter) <= 2:
        return {'statusCode': 400, 'result':'The keyword length must be greater than 3.'}
    # (38661, 'KR', 'hosting', 405760, 'abcle', '', datetime.datetime(2025, 1, 4, 3, 47, 37))
    citys = data_layer.get_cityobject_by_keyword(filter)
    return {
        'statusCode': 200,
        'result': citys
    }

def is_ip_address(ip_string):
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False

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
    city_id = data_layer.get_cityid_by_ip(requests['srcip'])
    if requests['method'] == 'POST':
        jobResult = json.loads(requests['body'])
        if 'next' in requests['query']:
            next = requests['query']['next']
        else:
            next = ''
        # print(f"receive {len(jobResult)} job")
        for obj in jobResult:
            jobtype = obj['jobid'][:4]
            jobid = int(obj['jobid'][4:])
            if jobtype == 'ping':
                # obj['status'] = 0 success 256 partial success or not found any pingable ip
                # obj['stderr'] -> 1.6.81.7 : duplicate for [0], 64 bytes, 468 ms
                stdout = obj['stdout'].split('\n')
                ips = []
                for out in stdout:
                    # Enough hosts reachable (required: 100, reachable: 100)
                    if out == '' or out.startswith('[DEBUG]'):
                        continue
                    if is_ip_address(out):
                        ips.append(out)
                #print(f"pingjob: {jobid} status: {obj['status']} ips: {len(ips)}")
                # print(ips)
                if len(ips) > 0:
                    data_layer.update_pingable_ip(jobid, ips)
            elif jobtype == 'data':
                #print(f"datajob: {jobid} status: {obj['status']}")
                #print(obj['stdout'])
                #print(obj['stderr'])
                # stdout:
                # [DEBUG] CPU time used: 0.083289 sec
                # stderr:
                # 2.17.168.71 : 370 370 370 370 373 370 370 370 370 370 370
                # 2.17.168.93 : 358 358 358 358 363 358 358 358 358 358 358
                # 2.17.168.76 : 358 358 358 358 358 359 358 358 358 358 358
                samples = []
                for stderr in obj['stderr'].split('\n'):
                    for data in stderr.split(' '):
                        try:
                            samples.append(float(data))
                        except ValueError:
                            pass
                n = len(samples)
                if len(samples)>0:
                    # numpy 库太大了，这里简单实现一下
                    # arr = np.array(samples)
                    sorted_data = sorted(samples)
                    datas = {
                        'src_city_id': city_id,
                        'dist_city_id': jobid,
                        'samples': n,
                        'latency_min': int(sorted_data[0] * 1000), #min(samples), #np.min(arr),
                        'latency_max': int(sorted_data[n-1] * 1000), #max(samples), #np.max(arr),
                        'latency_avg': int(sum(sorted_data) * 1000 / n), #np.mean(arr),
                        'latency_p50': int(data_layer.np_percentile(sorted_data, 50) * 1000), #np.percentile(arr, 50),
                        'latency_p70': int(data_layer.np_percentile(sorted_data, 70) * 1000), #np.percentile(arr, 70),
                        'latency_p90': int(data_layer.np_percentile(sorted_data, 90) * 1000), #np.percentile(arr, 90),
                        'latency_p95': int(data_layer.np_percentile(sorted_data, 95) * 1000), #np.percentile(arr, 95),
                    }
                    data_layer.update_statistics_data(datas)
    if requests['useragent'].startswith('fping-pingable'):
        data_layer.update_client_status(requests['srcip'], 'ping')
        # get ping job here, ensure buffer data enough
        data_layer.refresh_iprange_check()
        for i in range(0, 20):
            obj = data_layer.cache_pop(settings.CACHEKEY_PINGABLE)
            if obj:
                stip = ipaddress.IPv4Address(obj['start_ip'])
                etip = ipaddress.IPv4Address(obj['end_ip'])
                #print(f"fetch ping job: {stip} {etip} {obj['city_id']}")
                ret["job"].append({
                    "jobid": 'ping' + str(obj['city_id']),
                    # disable stderr log here with 2> /dev/null , but it will cause error
                    # only found 100 max pingable ip to save time
                    "command": f"fping -g {stip} {etip} -r 2 -a -q -X 100",
                })
            else:
                break
        # print(f"fetch {len(ret['job'])} ping job")
        if len(ret["job"]) > 0:
            ret["next"] = 'ping'
            ret["interval"] = 1
    else:
        data_layer.update_client_status(requests['srcip'], 'data')
        for i in range(0, 10):
            job = data_layer.get_pingjob_by_cityid(city_id)
            #print(job)
            if job != None:
                ips = [str(ipaddress.IPv4Address(x)) for x in job['ips']]
                #print(f"fetch data job: {job['city_id']} {len(ips)}")
                ret["job"].append({
                    "jobid": 'data' + str(job['city_id']),
                    "command": "fping -a -q -C 11 " + ' '.join(ips),
                })
            else:
                break
        # print(f"fetch {len(ret['job'])} data job")
        if len(ret['job']) > 0:
            ret["next"] = "data"
            ret["interval"] = 1
    return {
        'statusCode': 200,
        'result': ret
    }

def lambda_handler(event, context):
    # print(event)
    requests = {'version': '1.0'}
    if 'version' in event:
        # 兼容 API Gateway
        # https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
        if event['version'] == '2.0':
            requests = {
                'version': 'apigw-httpapi2.0',
                'srcip': event['requestContext']['http']['sourceIp'],
                'useragent': event['requestContext']['http']['userAgent'],
                'method': event['requestContext']['http']['method'],
                'body': event['body'] if 'body' in event else null,
                'path': event['requestContext']['http']['path'],
                'query': event['queryStringParameters'],
                'cookie': event['headers']['cookie'] if 'cookie' in event['headers'] else '',
            }
        elif event['version'] == '1.0':
            requests = {
                'version': 'apigw-httpapi1.0',
                'srcip': event['requestContext']['identity']['sourceIp'],
                'useragent': event['requestContext']['identity']['userAgent'],
                'method': event['requestContext']['httpMethod'],
                'body': event['body'],
                'path': event['requestContext']['path'],
                'query': event['queryStringParameters'],
                'cookie': event['headers']['cookie'] if 'cookie' in event['headers'] else '',
            }
    else:
        # 兼容 ALB
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
            'path': event['path'],
            'query': event['queryStringParameters'],
            'cookie': event['headers']['cookie'] if 'cookie' in event['headers'] else '',
        }
    requests['next'] = requests['query']['next'] if 'next' in requests['query'] else ''
    apimapping = {
        '/job':[fping_logic, settings.AUTH_NOTNEED],
        '/api/login': [webapi_login, settings.AUTH_NOTNEED],

        '/api/ipinfo': [webapi_ipinfo, settings.AUTH_BASEUSER],
        '/api/asninfo': [webapi_asninfo, settings.AUTH_BASEUSER],
        '/api/cityset': [webapi_cityset, settings.AUTH_BASEUSER],
        '/api/country': [webapi_country, settings.AUTH_BASEUSER],
        '/api/city': [webapi_city, settings.AUTH_BASEUSER],
        '/api/asn': [webapi_asn, settings.AUTH_BASEUSER],
        '/api/performance': [webapi_performance, settings.AUTH_BASEUSER],
        '/api/changepasswd': [webapi_changepasswd, settings.AUTH_BASEUSER],

        #'/api/status': [webapi_status, settings.AUTH_READONLY],
        '/api/statistics': [webapi_statistics, settings.AUTH_READONLY],

        '/api/runsql': [webapi_runsql, settings.AUTH_ADMIN],
        '/api/redis': [webapi_redis, settings.AUTH_ADMIN],
        '/api/updateuser': [webapi_updateuser, settings.AUTH_ADMIN],
    }
    if requests['path'] not in apimapping:
        if requests['useragent'].startswith('ELB-HealthChecker/2.0'):
            ret = {'statusCode':200, 'result':'healthly'}
        else:
            ret = {'statusCode':404, 'result':'not found'}
    else:
        print(requests)
        route = apimapping[requests['path']]
        if not data_layer.validate_user_cookies(route[1], requests['cookie']):
            ret = {'statusCode':403, 'result':'forbidden'}
        else:
            ret = route[0](requests)
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