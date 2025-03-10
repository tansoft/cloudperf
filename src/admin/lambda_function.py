import json
import os
import zipfile
import boto3
from urllib.parse import urlparse
import data_layer
import settings
import secrets
import string

def download_from_s3(s3_path):
    """
    Download file from S3
    Args:
        s3_path: S3 URL (s3://bucket-name/path/to/file)
    Returns:
        str: Path to downloaded file
    """
    parsed = urlparse(s3_path)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    
    # Create temp directory if it doesn't exist
    temp_dir = '/tmp/s3_files'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Download file
    local_path = os.path.join(temp_dir, os.path.basename(key))
    s3_client = boto3.client('s3')
    print(f'download file form s3://{bucket}/{key} to {local_path}')
    s3_client.download_file(bucket, key, local_path)
    
    return local_path

def get_city_id(ip:str):
    cityid = data_layer.get_cityid_by_ip(ip)
    return cityid

def exec_sql(sql):
    if sql == 'init_db':
        return data_layer.mysql_create_database()
    ret = data_layer.mysql_batch_execute(sql)
    return {
        "status": 200,
        "msg": ret
    }

def exec_sqlfile(sql_file):
    """
    Execute SQL from a file or zip archive, supporting both local and S3 files
    Args:
        sql_file: Path to .sql file or .zip containing SQL files
                 Can be local path or S3 URL (s3://bucket-name/path/to/file)
    Returns:
        dict: Execution result
    """
    try:
        print(f'exec_sql {sql_file}')
        # Handle S3 files
        if sql_file.startswith('s3://'):
            local_file = download_from_s3(sql_file)
            sql_file = local_file

        # Handle zip files
        if sql_file.endswith('.zip'):
            temp_dir = '/tmp/sql_files'
            os.makedirs(temp_dir, exist_ok=True)
            
            with zipfile.ZipFile(sql_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            results = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    print(f'exec_sql zipfile {file}')
                    if file.endswith('.sql'):
                        sql_path = os.path.join(root, file)
                        with open(sql_path, 'r') as f:
                            sql_content = f.read()
                        data_layer.mysql_batch_execute(sql_content)
                        print(f'exec_sql zipfile {file} finish.')
                        results.append(f'Executed {file}')
            
            # Cleanup
            os.system(f'rm -rf {temp_dir}')
            return {
                'status': 200,
                'msg': 'Executed all SQL files from zip',
                'details': results
            }
        
        # Handle SQL files
        elif sql_file.endswith('.sql'):
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            data_layer.mysql_batch_execute(sql_content)
            print(f'exec_sql {sql_file} finish.')
            return {
                'status': 200,
                'msg': f'Executed SQL file: {sql_file}'
            }
        
        else:
            return {
                'status': 404,
                'msg': 'Invalid file type. Must be .sql or .zip'
            }
            
    except Exception as e:
        return {
            'status': 500,
            'msg': str(e)
        }
    finally:
        # Cleanup any downloaded S3 files
        if sql_file.startswith('/tmp/s3_files/'):
            try:
                os.remove(sql_file)
            except:
                pass

def create_user(username):
    password = secrets.choice(string.ascii_uppercase) + ''.join(secrets.choice(string.ascii_lowercase) for _ in range(3)) + ''.join(secrets.choice(string.digits) for _ in range(3)) + secrets.choice(".,;@#$%^!")
    print(f'generate password for {username}: {password}')
    ret = data_layer.create_user(username, password, settings.AUTH_ADMIN)
    print(ret)
    return ret

# Example usage:
# event = {"action":"exec_sqlfile","param":"update.sql"}
# event = {"action":"exec_sqlfile","param":"updates.zip"}
# event = {"action":"exec_sqlfile","param":"s3://my-bucket/sql/update.sql"}
# event = {"action":"exec_sqlfile","param":"s3://my-bucket/sql/updates.zip"}
# event = {"action":"exec_sql","param":"init_db"}
# event = {"action":"exec_sql","param":"select * from asn;"}
# event = {"action":"create_user","param":"myuser"}
# or s3 notify message
def lambda_handler(event, context):
    try:
        # Handle S3 notifications
        ret = {"status":404, "msg":"not found"}
        if 'Records' in event:
            for record in event['Records']:
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                event_name = record['eventName']
                print(f"Processing event {event_name} exec_sql for {bucket}/{key}")
                ret = exec_sqlfile(f's3://{bucket}/{key}')
            return ret

        # Handle direct function calls
        action = event.get('action')
        if not action:
            return ret

        # Get the function from current module's globals
        func = globals().get(action)
        if not func or not callable(func):
            return {"status": 404, "msg": f"Action '{action}' not found or not callable"}

        param = event.get('param')
        print(f'process action: {action} param: {param}')
        if param:
            ret = func(param)
        else:
            ret = func()
        return ret

    except Exception as e:
        return {
            "status": 500,
            "msg": f"Error processing request: {str(e)}"
        }

# local test
if __name__ == "__main__":
    import sys
    print(sys.argv[1])
    ret = lambda_handler(json.loads(sys.argv[1]), None)
    print(ret)