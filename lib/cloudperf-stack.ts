import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as lambda from 'aws-cdk-lib/aws-lambda';
//import * as events from 'aws-cdk-lib/aws-events';
//import * as events_targets from 'aws-cdk-lib/aws-events-targets';
//import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as cr from 'aws-cdk-lib/custom-resources';
//import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as targets from 'aws-cdk-lib/aws-elasticloadbalancingv2-targets';
import * as route53 from 'aws-cdk-lib/aws-route53';

const stackPrefix = 'cloudperf-';
const cidr = '10.0.0.0/16';

export class CloudperfStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, {
      ...props,
      env: {
        region: process.env.CDK_DEFAULT_REGION || 'us-east-1', // 指定默认区域
      }
    });

    // 为整个Stack添加标签
    cdk.Tags.of(this).add('CostCenter', stackPrefix + 'stack');

    // 创建 VPC
    const vpc = new ec2.Vpc(this, stackPrefix + 'vpc', {
      ipAddresses: ec2.IpAddresses.cidr(cidr),
      maxAzs: 2,
      natGateways: 1
    });
    const privateSubnetIds = vpc.privateSubnets.map(subnet => subnet.subnetId);

    // 创建 日志桶
    // 创建 S3 存储桶用于存储访问日志
    const logBucket = new s3.Bucket(this, 'log-', {
      removalPolicy: cdk.RemovalPolicy.DESTROY, // 仅用于测试，生产环境建议 RETAIN
      autoDeleteObjects: true, // 仅用于测试
      // 配置生命周期规则
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(30),
          transitions: [
            {
              storageClass: s3.StorageClass.INTELLIGENT_TIERING,
              transitionAfter: cdk.Duration.days(3)
            }
          ]
        }
      ]
    });

    // 创建 内网资源访问的安全组
    const sg = new ec2.SecurityGroup(this, 'int-sg', {
      vpc,
      description: 'Allow access to Internal Resource',
      allowAllOutbound: true
    });
    sg.addIngressRule(
      ec2.Peer.ipv4(cidr),
      ec2.Port.tcp(3306),
      'Allow MySQL access from Internal'
    );
    sg.addIngressRule(
      ec2.Peer.ipv4(cidr),
      ec2.Port.tcp(6379),
      'Allow ElastiCache access from Internal'
    );

    // 创建 Aurora Serverless V2 集群
    const db = new rds.DatabaseCluster(this, 'db-', {
      engine: rds.DatabaseClusterEngine.auroraMysql({ version: rds.AuroraMysqlEngineVersion.VER_3_07_1 }),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 128,
      writer: rds.ClusterInstance.serverlessV2('writer'),
      readers: [rds.ClusterInstance.serverlessV2('reader', { scaleWithWriter: true })],
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [sg],
    });

    // 创建 ElastiCache Serverless 集群
    const cacheCluster = new elasticache.CfnServerlessCache(this, stackPrefix + 'cache', {
      engine: 'valkey',
      serverlessCacheName: stackPrefix + 'cache',
      // securityGroupIds: ['securityGroupIds'],
      subnetIds: privateSubnetIds,
      securityGroupIds: [sg.securityGroupId],
    });

    // 创建项目使用的s3
    const s3Bucket = new s3.Bucket(this, 'data-', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // 创建 fping 任务
    // const fpingQueue = new sqs.Queue(this, stackPrefix + 'fping', {
    //  queueName: stackPrefix + 'fping',
    //  visibilityTimeout: cdk.Duration.minutes(15 * 4),
    //});

    // 创建 Lambda 工具层
    // fping 带有可执行的fping命令
    // const fpingLayer = new lambda.LayerVersion(this, stackPrefix + 'layer-fping', {
    //  code: lambda.Code.fromAsset('src/layer/fping-layer.zip'),
    //  compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
    //  license: 'Apache-2.0',
    //  description: 'A layer for fping',
    //});
    // pythonlib 包括 redis mysql 连接库等
    const pythonLayer = new lambda.LayerVersion(this, stackPrefix + 'layer-pythonlib', {
      code: lambda.Code.fromAsset('src/layer/pythonlib-layer.zip'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      license: 'Apache-2.0',
      description: 'A layer for pythonlib',
    });
    // data 层包括重用的数据访问函数等
    const dataLayer = new lambda.LayerVersion(this, stackPrefix + 'layer-data', {
      code: lambda.Code.fromAsset('src/layer/datalayer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      license: 'Apache-2.0',
      description: 'A layer for data',
    });

    const environments = {
      DB_WRITE_HOST: 'rds.cloudperf.vpc', // db.clusterEndpoint.hostname,
      DB_READ_HOST: 'rds-r.cloudperf.vpc', // db.clusterEndpoint.hostname, db.clusterReadEndpoint.hostname,
      DB_PORT: String(db.clusterEndpoint.port),
      DB_SECRET: db.secret?.secretArn || '',
      CACHE_HOST: 'redis.cloudperf.vpc', // cacheCluster.attrEndpointAddress,
      CACHE_PORT: cacheCluster.attrEndpointPort,
      // FPING_QUEUE: fpingQueue.queueUrl,
    };
    const web_environments = {
      AWS_LAMBDA_EXEC_WRAPPER: '/opt/bootstrap',
    }

    // 对外 api 接口函数
    const lambdaRoleApi = new iam.Role(this, 'role-api', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    const apiLambda = new lambda.Function(this, 'api', {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset('src/api'),
      handler: 'lambda_function.lambda_handler',
      vpc: vpc,
      vpcSubnets: { subnets: vpc.privateSubnets },
      role: lambdaRoleApi,
      timeout: cdk.Duration.minutes(5),
      layers: [pythonLayer, dataLayer],
      environment: environments,
      securityGroups: [sg],
    });

    // 提供系统的维护操作，包括初始化数据库等
    const lambdaRoleAdmin = new iam.Role(this, 'role-admin', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    const adminLambda = new lambda.Function(this, 'admin', {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset('src/admin'),
      handler: 'lambda_function.lambda_handler',
      vpc: vpc,
      vpcSubnets: { subnets: vpc.privateSubnets },
      role: lambdaRoleAdmin,
      timeout: cdk.Duration.minutes(15),
      layers: [pythonLayer, dataLayer],
      memorySize: 4096,
      ephemeralStorageSize: cdk.Size.gibibytes(8),
      environment: environments,
      securityGroups: [sg],
    });

    // 对外 api 服务
    const alb = new elbv2.ApplicationLoadBalancer(this, stackPrefix + 'api-alb', {
      vpc,
      internetFacing: true,
      vpcSubnets: { subnets: vpc.publicSubnets }
    });
    alb.logAccessLogs(logBucket, 'alb-logs');

    // fping 任务队列
    /*const lambdaRoleQueue = new iam.Role(this, 'role-queue', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    const api_environments = {
      ...environments,
      API_URL: alb.loadBalancerDnsName
    };
    const fpingQueueLambda = new lambda.Function(this, 'fping-queue', {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset('src/fping-queue'),
      handler: 'lambda_function.lambda_handler',
      role: lambdaRoleQueue,
      timeout: cdk.Duration.minutes(15),
      layers: [pythonLayer, fpingLayer],
      environment: environments,
    });
    const eventSource = new lambdaEventSources.SqsEventSource(fpingQueue, {
      batchSize: 1,
      maxBatchingWindow: cdk.Duration.seconds(60),
      maxConcurrency: 10
    });
    fpingQueueLambda.addEventSource(eventSource);*/

    // 对外 web 函数
    // https://github.com/awslabs/aws-lambda-web-adapter/tree/main/examples/nginx-zip
    const lambdaRoleWeb = new iam.Role(this, 'role-web', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    const webLambda = new lambda.Function(this, 'web', {
      runtime: lambda.Runtime.NODEJS_20_X,
      architecture: lambda.Architecture.X86_64,
      code: lambda.Code.fromAsset('src/web/lambda'),
      handler: 'bootstrap',
      role: lambdaRoleWeb,
      timeout: cdk.Duration.minutes(1),
      layers: [
        lambda.LayerVersion.fromLayerVersionArn(this, 'LambdaWebAdapter',
          `arn:aws:lambda:${this.region}:753240598075:layer:LambdaAdapterLayerX86:23`),
        lambda.LayerVersion.fromLayerVersionArn(this, 'Nginx',
          `arn:aws:lambda:${this.region}:753240598075:layer:Nginx123X86:12`),
      ],
      environment: web_environments,
    });

    // 定时任务
    /*const lambdaRoleCron = new iam.Role(this, 'role-cron', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    const cronLambda = new lambda.Function(this, 'cron', {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset('src/cron'),
      handler: 'lambda_function.lambda_handler',
      vpc: vpc,
      vpcSubnets: { subnets: vpc.privateSubnets },
      role: lambdaRoleCron,
      timeout: cdk.Duration.minutes(15),
      layers: [pythonLayer, dataLayer],
      environment: environments,
    });
    const cronRule = new events.Rule(this, 'MinutelyCronRule', {
      schedule: events.Schedule.rate(cdk.Duration.minutes(1)), // events.Schedule.expression('cron(0/1 * * * ? *)'),
    });
    cronRule.addTarget(new events_targets.LambdaFunction(cronLambda));*/

    // 生成各模块Policy
    const secretsManagerPolicyStatement = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret'
      ],
      resources: [db.secret?.secretArn || '']
    });
    const secretsManagerPolicy = new iam.Policy(this, stackPrefix + 'policy-SecretsManager', {
      statements: [secretsManagerPolicyStatement]
    })
    /*const sqsPolicyStatement = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['sqs:ReceiveMessage', 'sqs:DeleteMessage', 'sqs:GetQueueAttributes', 'sqs:SendMessage'],
      resources: [fpingQueue.queueArn],
    });
    const sqsPolicy = new iam.Policy(this, stackPrefix + 'policy-Sqs', {
      statements: [sqsPolicyStatement]
    })*/
    // 各lambda赋予权限
    lambdaRoleApi.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));
    lambdaRoleApi.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaVPCAccessExecutionRole"));
    lambdaRoleApi.attachInlinePolicy(secretsManagerPolicy);

    lambdaRoleAdmin.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));
    lambdaRoleAdmin.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaVPCAccessExecutionRole"));
    lambdaRoleAdmin.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonS3ReadOnlyAccess"));
    lambdaRoleAdmin.attachInlinePolicy(secretsManagerPolicy);

    //lambdaRoleQueue.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));
    //lambdaRoleQueue.attachInlinePolicy(sqsPolicy);

    lambdaRoleWeb.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));

    /*lambdaRoleCron.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));
    lambdaRoleCron.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaVPCAccessExecutionRole"));
    lambdaRoleCron.attachInlinePolicy(secretsManagerPolicy);
    lambdaRoleCron.attachInlinePolicy(sqsPolicy);*/

    // 数据处理流程
    const s3nadmin = new s3n.LambdaDestination(adminLambda);
    s3Bucket.addEventNotification(s3.EventType.OBJECT_CREATED, s3nadmin, { prefix: 'import-sql/', suffix: '.sql' });
    s3Bucket.addEventNotification(s3.EventType.OBJECT_CREATED, s3nadmin, { prefix: 'import-sql/', suffix: '.zip' });
    // 创建Custom Resource来调用Admin Lambda中的初始化
    new cr.AwsCustomResource(this, 'InvokeLambda', {
      onCreate: {
        service: 'Lambda',
        action: 'invoke',
        parameters: {
          FunctionName: adminLambda.functionName,
          Payload: JSON.stringify({ 'action': 'exec_sql', 'param': 'init_db' }),
        },
        physicalResourceId: cr.PhysicalResourceId.of('InvokeLambda'),
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['lambda:InvokeFunction'],
          resources: [adminLambda.functionArn],
        }),
      ]),
    });
    // 上传建表sql，会触发自动运行
    new s3deploy.BucketDeployment(this, 'data', {
      sources: [s3deploy.Source.asset('src/data')],
      destinationBucket: s3Bucket,
    });

    // alb 配置
    const listener = alb.addListener(stackPrefix + 'api-listener', {
      port: 80,
      open: true
    });

    listener.addTargets(stackPrefix + 'web-target', {
      targets: [new targets.LambdaTarget(webLambda)],
      healthCheck: { enabled: false, path: '/' },
    });

    listener.addTargets(stackPrefix + 'api-target', {
      targets: [new targets.LambdaTarget(apiLambda)],
      healthCheck: { enabled: false, path: '/' },
      priority: 10,
      conditions: [
        elbv2.ListenerCondition.pathPatterns(['/job*', '/api*'])
      ]
    });

    // 根目录访问，只有带上参数 query=login，才允许通过
    listener.addTargets(stackPrefix + 'frist-login', {
      targets: [new targets.LambdaTarget(webLambda)],
      healthCheck: { enabled: false, path: '/' },
      priority: 20,
      conditions: [elbv2.ListenerCondition.queryStrings([{ key: 'query', value: 'login' }])]
    });
    // 阻止直接对外措施
    listener.addAction(stackPrefix + 'disable-root', {
      priority: 21,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/', '/index.html'])],
      action: elbv2.ListenerAction.fixedResponse(403, { contentType: 'text/plain', messageBody: 'Forbidden' })
    });

    const albLogDeliveryPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:PutObject'],
      resources: [`${logBucket.bucketArn}/alb-logs/*`],
      principals: [new iam.ServicePrincipal('delivery.logs.amazonaws.com')]
    });
    logBucket.addToResourcePolicy(albLogDeliveryPolicy);

    // 内部域名映射
    const hostedZone = new route53.PrivateHostedZone(this, 'vpc', {
      zoneName: 'cloudperf.vpc',
      vpc: vpc
    });
    new route53.CnameRecord(this, 'RedisRecord', {
      zone: hostedZone,
      recordName: 'redis',
      domainName: cacheCluster.attrEndpointAddress,
      ttl: cdk.Duration.minutes(5)
    });
    new route53.CnameRecord(this, 'RDSRecord', {
      zone: hostedZone,
      recordName: 'rds',
      domainName: db.clusterEndpoint.hostname,
      ttl: cdk.Duration.minutes(5)
    });
    new route53.CnameRecord(this, 'RDSRRecord', {
      zone: hostedZone,
      recordName: 'rds-r',
      domainName: db.clusterReadEndpoint.hostname,
      ttl: cdk.Duration.minutes(5)
    });
    new route53.CnameRecord(this, 'APIRecord', {
      zone: hostedZone,
      recordName: 'api',
      domainName: alb.loadBalancerDnsName,
      ttl: cdk.Duration.minutes(5)
    });

    // 输出变量
    new cdk.CfnOutput(this, 'dbHost', {
      value: db.clusterEndpoint.hostname,
      description: 'DB endpoint'
    });

    new cdk.CfnOutput(this, 'dbReadHost', {
      value: db.clusterReadEndpoint.hostname,
      description: 'DB read endpoint'
    });

    new cdk.CfnOutput(this, 'dbSecret', {
      value: db.secret?.secretArn || '',
      description: 'DB Secret'
    });

    new cdk.CfnOutput(this, 'cacheHost', {
      value: cacheCluster.attrEndpointAddress,
      description: 'Cache endpoint'
    });

    new cdk.CfnOutput(this, 'albHost', {
      value: alb.loadBalancerDnsName,
      description: 'ALB endpoint'
    });

    new cdk.CfnOutput(this, 'intSG', {
      value: sg.securityGroupId,
      description: 'Internal Security Group ID'
    });

    //new cdk.CfnOutput(this, 'fpingQueue', {
    //  value: fpingQueue.queueArn,
    //  description: 'fping job queue'
    //});

    new cdk.CfnOutput(this, 's3Bucket', {
      value: s3Bucket.bucketArn,
      description: 'data exchange'
    });

    new cdk.CfnOutput(this, 'adminLambda', {
      value: adminLambda.functionName,
      description: 'admin Lambda'
    });

  }
}
