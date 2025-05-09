import boto3
import json
import os

CACHE_BASE_TTL=3600
CACHE_LONG_TTL=86400

# 用于sql查询的缓存
CACHEKEY_SQL = 'sql'
# 用于可ping ip任务的缓存
CACHEKEY_PINGABLE = 'ping'
# 用于测试延迟任务的缓存
CACHEKEY_CITYJOB = 'job'
# 用于报告在线客户端
CACHEKEY_ONLINE_SERVERS = 'online'
# 用于报告最近处理任务数
CACHEKEY_RECENT_TASKS = 'task'
# 用于登录用户授权
CACHEKEY_USERAUTH = 'user'
# 用于暂停客户端任务，value为重试时间，如3600秒
CACHEKEY_PAUSE = 'pause'

# 每个cityid对保存的最新记录条数，默认7次
MAX_RECORDS_PER_CITYID = 7

# 可ping ip的存活时间，只用最近4次就可以了
STABLE_PINGABLE_IP = '15' # 1111b
NEW_PINGABLE_IP = '8' # 1000b
LOSS_PINGABLE_IP = '7' # 0111b
DELETE_PINGABLE_IP = '0' # 00000000b
#STABLE_PINGABLE_IP = '240' # 11110000b
#NEW_PINGABLE_IP = '128' # 10000000b
#LOSS_PINGABLE_IP = '127' # 01111111b

# 权限划分
# 不需要授权
AUTH_NOTNEED = 0
# 普通用户
AUTH_BASEUSER = 1
# 系统维护用户，可查看系统状态信息，连接readonly数据库
AUTH_READONLY = 1 | 2
# 系统管理员
AUTH_ADMIN = 1 | 2 | 4

S3_BUCKET = os.environ.get('S3_BUCKET', 'cloudperf')

CACHE_HOST = os.environ.get('CACHE_HOST', 'redis.cloudperf.vpc')
CACHE_PORT = int(os.environ.get('CACHE_PORT', '6379'))

DB_READ_HOST = os.environ.get('DB_READ_HOST', 'rds-r.cloudperf.vpc')
DB_WRITE_HOST = os.environ.get('DB_WRITE_HOST', 'rds.cloudperf.vpc')
DB_PORT = int(os.environ.get('DB_PORT', '3306'))
DB_DATABASE='cloudperf'
DB_SECRET = os.environ.get('DB_SECRET', '')
if DB_SECRET != '':
    secrets_manager = boto3.client('secretsmanager')
    valobj = secrets_manager.get_secret_value(SecretId=DB_SECRET)
    secret_dict = json.loads(valobj['SecretString'])
    DB_USER = secret_dict['username']
    DB_PASS = secret_dict['password']
else:
    DB_USER = os.environ.get('DB_USER', '')
    DB_PASS = os.environ.get('DB_PASS', '')
