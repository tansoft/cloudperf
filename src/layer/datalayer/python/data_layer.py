import ipaddress
import pymysql
import redis
import re
import json
import settings
import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError

redis_pool = redis.ConnectionPool(
    host=settings.CACHE_HOST,
    port=settings.CACHE_PORT,
    decode_responses=True,
    connection_class=redis.SSLConnection,
    socket_timeout=5,
    socket_connect_timeout=5)

def mysql_create_database(database:str = None):
    if database == None:
        database = settings.DB_DATABASE
    conn = pymysql.connect(host=settings.DB_WRITE_HOST, user=settings.DB_USER, passwd=settings.DB_PASS, charset='utf8mb4', port=settings.DB_PORT)
    cursor = conn.cursor()
    try:
        sql = "CREATE DATABASE IF NOT EXISTS `" + database + "` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
        cursor.execute(sql)
        ret = cursor.fetchall()
    except Exception as e:
        print(f"Error executing SQL script: {e}")
        conn.rollback()
        ret = False
    finally:
        cursor.close()
        conn.close()
    return ret

def safe_like_pattern(search:str):
    return search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    # return search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').replace('"','').replace("'",'')

def fetch_all_to_dict(cursor: pymysql.cursors.Cursor) -> List[Dict[str, Any]]:
    """
    将 cursor.fetchall() 的结果转换为字典列表
    参数：
    cursor: PyMySQL 游标对象
    返回：
    List[Dict[str, Any]]: 包含查询结果的字典列表
    """
    # 获取列名
    columns = [col[0] for col in cursor.description]
    # 获取所有行
    rows = cursor.fetchall()
    # 转换为字典列表
    return [dict(zip(columns, row)) for row in rows]

# 执行写
def mysql_execute(sql:str, obj = None):
    #pymysql.connections.DEBUG = True
    conn = pymysql.connect(host=settings.DB_WRITE_HOST, user=settings.DB_USER, passwd=settings.DB_PASS, db=settings.DB_DATABASE, charset='utf8mb4', port=settings.DB_PORT)
    cursor = conn.cursor()
    cursor.execute(sql, obj)
    results = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return results

def mysql_select(sql:str, obj = None, fetchObject = True):
    conn = pymysql.connect(host=settings.DB_READ_HOST, user=settings.DB_USER, passwd=settings.DB_PASS, db=settings.DB_DATABASE, charset='utf8mb4', port=settings.DB_PORT)
    cursor = conn.cursor()
    cursor.execute(sql, obj)
    if fetchObject:
        results = fetch_all_to_dict(cursor)
    else:
        results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

# 会打印结果
def mysql_batch_execute(sql: str):
    results = []
    try:
        conn = pymysql.connect(
            host=settings.DB_WRITE_HOST,
            user=settings.DB_USER,
            passwd=settings.DB_PASS,
            db=settings.DB_DATABASE,
            charset='utf8mb4',
            port=settings.DB_PORT,
            client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
        )
        cursor = conn.cursor()

        # 分割SQL语句
        sql_statements = sql.strip().split(";")
        
        affected_rows = 0
        # 执行每条SQL语句
        for sql in sql_statements:
            sql = sql.strip()
            if sql:  # 忽略空语句
                cursor.execute(sql)
                if sql.lower().startswith("select"):
                    # 查询语句
                    rows = cursor.fetchall()
                    if rows:
                        columns = [desc[0] for desc in cursor.description]
                        print("列名:", " | ".join(columns))
                        for row in rows:
                            print(" | ".join(map(str, row)))
                        results.append({
                            'sql': sql,
                            'type': 'query',
                            'columns': ','.join(columns), #columns,
                            'rows': [','.join(map(str, row)) for row in rows] # [list(map(str, row)) for row in rows]
                        })
                    else:
                        print('无结果返回')
                        results.append({
                            'sql': sql,
                            'type': 'query',
                            'message': '无结果返回'
                        })
                else:
                    affected_rows += cursor.rowcount
                    # print(f"影响行数: {cursor.rowcount}")
                    # 非查询语句
                    results.append({
                        'sql': sql,
                        'type': 'update',
                        'affected_rows': cursor.rowcount
                    })
                conn.commit()
        if affected_rows > 0:
            print(f"共影响行数: {affected_rows}")

    except Exception as e:
        print(f"{sql}\n错误: {str(e)}")
        results.append({'error': str(e)})

    finally:
        if 'conn' in locals():
            conn.close()
    return results

def mysql_print_results(results):
    """打印执行结果"""
    for result in results:
        if 'error' in result:
            print(f"\n错误: {result['error']}")
            continue
        print(f"\n执行SQL: {result['sql']}")        
        if result['type'] == 'query':
            if 'columns' in result:
                print("列名:", " | ".join(result['columns']))
                for row in result['rows']:
                    print(" | ".join(map(str, row)))
            else:
                print(result['message'])
        else:
            print(f"影响行数: {result['affected_rows']}")   

def mysql_batch_runsql(sql:str):
    ret = True
    # Enable multi-statements in connection
    conn = pymysql.connect(
        host=settings.DB_WRITE_HOST,
        user=settings.DB_USER,
        passwd=settings.DB_PASS,
        db=settings.DB_DATABASE,
        charset='utf8mb4',
        port=settings.DB_PORT,
        client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
    )
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        # Handle multiple result sets
        while True:
            try:
                cursor.fetchall()
                if not cursor.nextset():
                    break
            except:
                pass
        conn.commit()
    except Exception as e:
        print(f"Error executing SQL script: {e}")
        conn.rollback()
        ret = False
    finally:
        cursor.close()
        conn.close()
    return ret

def mysql_runsql(sql:str, obj = None):
    conn = pymysql.connect(host=settings.DB_WRITE_HOST, user=settings.DB_USER, passwd=settings.DB_PASS, db=settings.DB_DATABASE, charset='utf8mb4', port=settings.DB_PORT)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, obj)
        ret = cursor.fetchall()
    except Exception as e:
        print(f"Error executing SQL script: {e}")
        conn.rollback()
        ret = False
    finally:
        cursor.close()
        conn.close()
    return ret

def mysql_select_onevalue(sql:str, obj = None, default = 0):
    row = mysql_select(sql, obj, False)
    if row == None or len(row) == 0:
        return default
    return row[0][0]

def cache_get(key:str):
    try:
        r = redis.StrictRedis(connection_pool=redis_pool)
        ret = r.get(key)
        if ret:
            ret = json.loads(ret)
        return ret
    except Exception as e:
        print('cache get failed.', repr(e))
        return None

def cache_set(key:str, value, ttl:int = settings.CACHE_BASE_TTL):
    try:
        r = redis.StrictRedis(connection_pool=redis_pool)
        print('cache set:', key, ttl, value)
        return r.setex(key, ttl, json.dumps(value))
    except Exception as e:
        print('cache set failed.', repr(e) , key, ttl, value)
        return None

def cache_delete(key:str):
    try:
        r = redis.StrictRedis(connection_pool=redis_pool)
        print('cache delete:', key)
        return r.delete(key)
    except Exception as e:
        print('cache delete failed.', repr(e), key)
        return None

def cache_push(key:str, value, ttl:int = settings.CACHE_BASE_TTL):
    try:
        r = redis.StrictRedis(connection_pool=redis_pool)
        return r.rpush(key, json.dumps(value))
    except Exception as e:
        print('cache push failed.', repr(e), key, value)
        return None

def cache_pop(key:str):
    try:
        r = redis.StrictRedis(connection_pool=redis_pool)
        ret = r.lpop(key)
        if ret:
            ret = json.loads(ret)
        return ret
    except Exception as e:
        print('cache pop failed.', repr(e), key)
        return None

def cache_listlen(key:str):
    try:
        r = redis.StrictRedis(connection_pool=redis_pool)
        return r.llen(key)
    except Exception as e:
        print('cache list len failed.', repr(e), key)
        return 0

def cache_mysql_get_onevalue(sql:str, default = 0, ttl:int = settings.CACHE_BASE_TTL):
    key = f'{settings.CACHEKEY_SQL}ov_{hash(sql)}'
    val = cache_get(key)
    if val != None:
        return val
    ret = mysql_select_onevalue(sql, default = default)
    cache_set(key, ret, ttl)
    return ret

def delete_mysql_select_cache(sql:str, obj = None, fetchObject = True):
    key = f'{settings.CACHEKEY_SQL}sl_{hash(sql)}{hash(obj)}{hash(fetchObject)}'
    return cache_delete(key)

def cache_mysql_select(sql:str, obj = None, fetchObject = True, ttl:int = settings.CACHE_BASE_TTL):
    key = f'{settings.CACHEKEY_SQL}sl_{hash(sql)}{hash(obj)}{hash(fetchObject)}'
    val = cache_get(key)
    if val != None:
        return val
    ret = mysql_select(sql, obj, fetchObject)
    cache_set(key, ret, ttl)
    return ret

def get_countrys():
    return cache_mysql_select('select code,name from country order by code', ttl=settings.CACHE_LONG_TTL)

def get_citys_by_country_code(country_code):
    return cache_mysql_select(
        'SELECT name as id,name,latitude,longitude FROM city WHERE country_code = %s GROUP BY name', (country_code,))

def get_cityobject(filter:str, obj = None, limit:int = 50):
    return cache_mysql_select('''
select c.id as cityId,a.asn as asn,c.country_code as country,
COALESCE(c.friendly_name, c.name) as name,c.region as region,
a.name as asnName, a.domain as domain,
c.latitude as latitude, c.longitude as longitude,
a.type as asnType,a.ipcounts as ipcounts,
INET_NTOA(i.start_ip) as startIp, INET_NTOA(i.end_ip) as endIp from city as c, asn as a,iprange as i
 where c.id = i.city_id and c.asn=a.asn and ''' + filter + f' limit {limit}', obj)

def get_asns_by_country_city(country_code, city_name):
    return get_cityobject("c.country_code = %s and c.name = %s group by c.id,c.asn",(country_code,city_name,))

def get_cityobject_by_ip(ip:str):
    ipno = ipaddress.IPv4Address(ip)._ip
    return get_cityobject("i.start_ip<=%s and i.end_ip>=%s group by c.id", (ipno,ipno))

def get_cityobject_by_id(id:int):
    return get_cityobject("c.id=%s group by c.id",(id,),limit=1)

def get_cityobject_by_keyword(keyword:str, limit=50):
    if keyword.lower().startswith('as'):
        keyword = keyword.lower().replace('asn','').replace('as','')

    if keyword.isdecimal():
        filter = f'a.asn={keyword}'
        obj = None
    else:
        filter = """ CONCAT_WS('',c.name, c.friendly_name, c.region, a.name, a.domain) LIKE %s ESCAPE '\\\\' group by c.id """
        keyword = safe_like_pattern(keyword)
        obj = (f"%{keyword}%",)
    return get_cityobject(filter, obj, limit)

def get_latency_data_cross_city(sourceCityId:str, destCityId:str):
    pattern = r'^[\d,]+$'
    print('query with:', sourceCityId, destCityId)
    if not bool(re.match(pattern, sourceCityId)) or not bool(re.match(pattern, destCityId)):
        return None
    return cache_mysql_select(f'''
select src_city_id as src, dist_city_id as dist, sum(samples) as samples,
min(latency_min) as min,max(latency_max) as max,avg(latency_avg) as avg,avg(latency_p50) as p50,
avg(latency_p70) as p70,avg(latency_p90) as p90,avg(latency_p95) as p95
from statistics where src_city_id in ({sourceCityId}) and dist_city_id in ({destCityId}) group by src_city_id,dist_city_id
''')

CITYSET_DEFAULT_CACHE_SQL = 'select id,name,cityids as cityIds from `cityset`'

def get_citysets():
    return cache_mysql_select(CITYSET_DEFAULT_CACHE_SQL)

def add_cityset(name:str, city_ids:list):
    ret = mysql_execute('INSERT into `cityset`(`name`,`cityids`) values(%s,%s)', (name, ','.join(city_ids)))
    delete_mysql_select_cache(CITYSET_DEFAULT_CACHE_SQL)
    return ret

def edit_cityset(id:int, name:str, city_ids:list):
    ret = mysql_execute('UPDATE `cityset` set name=%s,cityids=%s where id=' + str(id), (name, ','.join(city_ids)))
    delete_mysql_select_cache(CITYSET_DEFAULT_CACHE_SQL)
    return ret

def del_cityset(id:int):
    ret = mysql_execute('delete from `cityset` where id=' + str(id))
    delete_mysql_select_cache(CITYSET_DEFAULT_CACHE_SQL)
    return ret

def check_expired_iprange(days, limit):
    return mysql_select('select start_ip,end_ip,city_id from iprange where lastcheck_time < date_sub(now(), interval %s day) order by lastcheck_time limit %s', (days, limit))

def update_pingable_result(city_id, start_ip, end_ip):
    # 通过 start_ip end_ip city_id 来更新对应 pingable 表的数据，更新 lastresult 右移1位高位为0，表示这个ip最新数据没有更新了
    mysql_execute('update pingable set lastresult=lastresult>>1 where city_id=%s and ip>=%s and ip<=%s', (city_id, start_ip, end_ip))
    # 检查 pingable 表，删除 lastresult 全为 0 的条目，因为该ip已经连续不可ping了（就算新的任务他又可ping了，重新插入就是）
    mysql_execute('delete from pingable where lastresult=0')
    # 更新 lastcheck_time 时间，避免马上再次检查
    mysql_execute('update iprange set lastcheck_time = CURRENT_TIMESTAMP where city_id=%s and start_ip=%s', (city_id, start_ip))

def update_pingable_ip(city_id, ips):
    for ip in ips:
        ipno = ipaddress.IPv4Address(ip)._ip
        # 128 = 10000000b
        mysql_execute('INSERT INTO `pingable`(`ip`,`city_id`,`lastresult`) VALUES(%s, %s, 128) ON DUPLICATE KEY UPDATE lastresult=lastresult|128', (ipno, city_id))

# 已知国家数量，已知city数量，已知asn数量
# 稳定可ping数量，新增可ping数量，最近不可ping数量
# 可用cidr数量，过期cidr数量，cidr队列长度
# 已知cityid数量，可ping的cityid数量，有数据的cityid pair数量
def query_statistics_data(datas = 'all-country,all-city,all-asn,ping-stable,ping-new,ping-loss,cidr-ready,cidr-outdated,cidr-queue,cityid-all,cityid-ping,cityid-pair'):
    supports = {
        'all-country':'select count(1) from country',
        'all-city':'select count(1) from (select country_code,name from city group by country_code,name) as a',
        'all-asn':'select count(1) from asn',
        # 240 = 11110000
        'ping-stable':'select count(1) from pingable where lastresult>=240',
        'ping-new':'select count(1) from pingable where lastresult>=128',
        'ping-loss':'select count(1) from pingable where lastresult<=127',

        'cidr-ready':'select count(1) from iprange where lastcheck_time >= date_sub(now(), interval 14 day)',
        'cidr-outdated':'select count(1) from iprange where lastcheck_time < date_sub(now(), interval 14 day)',
        'cidr-queue':'',

        'cityid-all':'select count(1) from city',
        'cityid-ping':'select count(1) from (select city_id from pingable where lastresult>0 group by city_id) as a',
        'cityid-pair':'select count(1) from (select src_city_id,dist_city_id from statistics group by src_city_id,dist_city_id) as a'
    }
    outs = {}
    for data in datas.split(','):
        if data == 'cidr-queue':
            outs[data] = cache_listlen(settings.CACHEKEY_PINGABLE)
        else:
            outs[data] = mysql_select_onevalue(supports[data])
    return outs

def send_sqs_messages_batch(queue_url: str, messages: List[Dict[str, Any]]) -> Dict:
    """
    批量发送 JSON 消息到 SQS 队列
    Args:
        queue_url (str): SQS 队列的 URL
        messages (List[Dict]): JSON 消息列表
    
    Returns:
        Dict: 发送结果，包含成功和失败的消息
    """
    sqs = boto3.client('sqs')
    # 准备批量发送的条目，将消息转换为 JSON 字符串
    entries = [
        {
            'Id': str(i),  # 批次中消息的唯一标识
            'MessageBody': json.dumps(message)  # 将字典转换为 JSON 字符串
        }
        for i, message in enumerate(messages)
    ]
    # 每批最多发送 10 条消息
    results = {
        'successful': [],
        'failed': []
    }
    # 分批处理
    for i in range(0, len(entries), 10):
        batch = entries[i:i + 10]
        try:
            response = sqs.send_message_batch(
                QueueUrl=queue_url,
                Entries=batch
            )
            # 收集结果
            if 'Successful' in response:
                results['successful'].extend(response['Successful'])
            if 'Failed' in response:
                results['failed'].extend(response['Failed'])                
        except Exception as e:
            # 如果整个批次发送失败，将所有消息标记为失败
            failed_messages = [
                {
                    'Id': entry['Id'],
                    'Error': str(e)
                }
                for entry in batch
            ]
            results['failed'].extend(failed_messages)
    return results


def get_sqs_queue_size(queue_url: str) -> dict:
    """
    获取 SQS 队列的大小信息
    Args:
        queue_url (str): SQS 队列的 URL
    Returns:
        dict: 包含队列大小信息的字典
    """
    try:
        # 创建 SQS 客户端
        sqs = boto3.client('sqs')
        # 获取队列属性
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                'ApproximateNumberOfMessages',              # 可见消息数
                'ApproximateNumberOfMessagesNotVisible',    # 正在处理的消息数
                'ApproximateNumberOfMessagesDelayed'        # 延迟的消息数
            ]
        )
        # 提取队列大小信息
        queue_size = {
            'visible_messages': int(response['Attributes']['ApproximateNumberOfMessages']),
            'invisible_messages': int(response['Attributes']['ApproximateNumberOfMessagesNotVisible']),
            'delayed_messages': int(response['Attributes']['ApproximateNumberOfMessagesDelayed']),
            'total_messages': int(response['Attributes']['ApproximateNumberOfMessages']) + 
                            int(response['Attributes']['ApproximateNumberOfMessagesNotVisible']) + 
                            int(response['Attributes']['ApproximateNumberOfMessagesDelayed'])
        }
        return {
            'statusCode': 200,
            'queue_size': queue_size
        }
    except ClientError as e:
        return {
            'statusCode': 500,
            'error': str(e),
            'error_code': e.response['Error']['Code']
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'error': str(e)
        }

# step = /18 = 2^14
def split_ip_range(start_ip, end_ip, step = 16384):
    subnets = []
    i = start_ip
    while i <= end_ip:
        ei = min(i+step-1,end_ip)
        subnets.append([i, ei])
        #print(ipaddress.IPv4Address(i), ipaddress.IPv4Address(ei))
        i += step
    return subnets

# 由于 lambda 中 运行 fping 权限不够，所以不使用cron运行了，改为本地运行，因此使用redis队列来传递任务，通过api获取任务
def refresh_iprange_check(queue_url = ''):
    max_buffer_cidr = 100
    if queue_url != '':
        # 获取队列大小
        result = get_sqs_queue_size(queue_url)
        print(result)
        if result['statusCode'] != 200:
            return {
                'status': result['statusCode'],
                'msg': result['error']
            }
        len = result['queue_size']['visible_messages']
    else:
        # 检查 redis 队列长度
        len = cache_listlen(settings.CACHEKEY_PINGABLE)
    if len >= max_buffer_cidr:
        return {
            'status': 200,
            'msg': 'Queue is full, skip this round check'
        }

    # 检查 iprange 表，根据 lastcheck_time 排序，找出 lastcheck_time < now - 7days 的数据，准备进行更新
    datas = check_expired_iprange(days=14, limit=20)
    print(datas)
    # 通过 start_ip end_ip city_id 来更新对应 pingable 表的数据，更新 lastresult 右移1位高位为0，表示这个ip最新数据没有更新了
    # 检查 pingable 表，删除 lastresult 全为 0 的条目，因为该ip已经连续不可ping了（就算新的任务他又可ping了，重新插入就是）
    messages = []
    for data in datas:
        print(data)
        update_pingable_result(data['city_id'], data['start_ip'], data['end_ip'])
        subnets = split_ip_range(data['start_ip'], data['end_ip'])
        for subnet in subnets:
            messages.append({"type": "pingable", "start_ip": subnet[0], "end_ip": subnet[1], "city_id": data['city_id']})
    # 提交 start_ip end_ip city_id 的 ping 探测任务到 queue 中，queue 陆续完成探测任务时，会去更新对应 ip 的 lastresult 值，把新移位的值置为1000b，不存在的会插入
    if queue_url != '':
        result = send_sqs_messages_batch(queue_url, messages)
        print(result)
    else:
        for message in messages:
            result = cache_push(settings.CACHEKEY_PINGABLE, message)
    return {
        'status': 200,
        'msg': result
    }
