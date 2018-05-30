import boto3
import subprocess

# lambda role
role = 'arn:aws:iam::488538496950:role/tinker-access-lambda-role'

# lambda runtime
runtime = 'python3.6'

# function descriptions
functions = [
    {'function_name': 'tinker-access-stats', 'handler': 'tinker_access_histogram.lambda_generate_stats'}
]

# zip the latest code
subprocess.run(['zip', '/tmp/tinker_access.zip', 'tinker_access_histogram.py'], cwd='../src')
subprocess.run(['zip', '-ru', '/tmp/tinker_access.zip', 'resources'], cwd='../')

# upload the latest code to S3 bucket
code_bytes = open('/tmp/tinker_access.zip', 'rb').read()
s3 = boto3.client('s3')
s3.put_object(Bucket='tinker-access', Key='tinker_access.zip', Body=code_bytes)
code = 's3://tinker-access/tinker_access.zip'

# create lambda functions that don't exist
lbd = boto3.client('lambda')
functions_to_update = []
for f in functions:
    try:
        lbd.get_function(FunctionName=f['function_name'])
        functions_to_update.append(f)
    except Exception:
        lbd.create_function(
            FunctionName=f['function_name'],
            Runtime=runtime,
            Role=role,
            Handler=f['handler'],
            Code={
                'S3Bucket': 'tinker-access',
                'S3Key': 'tinker_access.zip'
            }
        )

# update lambda functions that already existed
for f in functions_to_update:
    lbd.update_function_code(
        FunctionName=f['function_name'],
        S3Bucket='tinker-access',
        S3Key='tinker_access.zip'
    )