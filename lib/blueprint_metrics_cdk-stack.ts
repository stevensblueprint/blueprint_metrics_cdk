import * as cdk from "aws-cdk-lib/core";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as iam from "aws-cdk-lib/aws-iam";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as path from "path";
import { Construct } from "constructs";

export interface BlueprintMetricsCdkStackProps extends cdk.StackProps {
  githubToken: string;
  discordWebhookUrl: string;
  googleWorkloadIdentityAudience: string;
  googleWorkloadIdentityServiceAccount: string;
}

export class BlueprintMetricsCdkStack extends cdk.Stack {
  constructor(
    scope: Construct,
    id: string,
    props: BlueprintMetricsCdkStackProps,
  ) {
    super(scope, id, props);
    const metricsConfigSecret = new secretsmanager.Secret(
      this,
      "MetricsConfigSecret",
      {
        secretName: "blueprint-metrics-config",
        description: "Configuration for Blueprint Metrics Lambda",
      },
    );

    const executionRole = new iam.Role(this, "BlueprintMetricsExecutionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      roleName: "bp-metrics-role",
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole",
        ),
      ],
    });

    executionRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["sts:GetCallerIdentity"],
        resources: ["*"],
      }),
    );

    const fn = new lambda.Function(this, "BlueprintMetricsFunction", {
      runtime: lambda.Runtime.PYTHON_3_14,
      handler: "main.handler",
      role: executionRole,
      functionName: "bp-metrics-fn",
      code: lambda.Code.fromAsset(path.join(__dirname, "../lambda"), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_14.bundlingImage,
          command: [
            "bash",
            "-c",
            [
              "set -euo pipefail",
              "pip install -r requirements.txt --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all: -t /asset-output",
              "cp -au *.py requirements.txt /asset-output",
              "find /asset-output -name '__pycache__' -prune -exec rm -rf {} +",
              "find /asset-output -name '*.pyc' -delete",
              "find /asset-output -type d \\( -name 'tests' -o -name 'test' \\) -prune -exec rm -rf {} + || true",
            ].join(" && "),
          ],
        },
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      description: "Lambda function for Blueprint Metrics",
      environment: {
        PROD: "true",
        METRICS_CONFIG_SECRET_ARN: metricsConfigSecret.secretArn,
        DISCORD_WEBHOOK_URL: props.discordWebhookUrl,
        GITHUB_TOKEN: props.githubToken,
        GOOGLE_WORKLOADIDENTITY_AUDIENCE: props.googleWorkloadIdentityAudience,
        GOOGLE_WORKLOADIDENTITY_SERVICEACCOUNT:
          props.googleWorkloadIdentityServiceAccount,
      },
    });

    metricsConfigSecret.grantRead(fn);

    const fnUrl = fn.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: ["*"],
        allowedMethods: [lambda.HttpMethod.POST],
      },
    });

    const scheduleRule = events.Schedule.cron({
      minute: "0",
      hour: "19",
      weekDay: "MON",
    });

    new events.Rule(this, "WeeklyMetricsRule", {
      schedule: scheduleRule,
      targets: [new targets.LambdaFunction(fn)],
    });

    new cdk.CfnOutput(this, "LambdaFunctionName", {
      value: fn.functionName,
    });

    new cdk.CfnOutput(this, "LambdaExecutionRoleName", {
      value: fn.role?.roleName || "",
    });

    new cdk.CfnOutput(this, "MetricsConfigSecretArn", {
      value: metricsConfigSecret.secretArn,
    });

    new cdk.CfnOutput(this, "LambdaFunctionUrl", {
      value: fnUrl.url,
    });
  }
}
