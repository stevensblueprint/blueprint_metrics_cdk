#!/usr/bin/env node
import * as cdk from "aws-cdk-lib/core";
import * as dotenv from "dotenv";
import { BlueprintMetricsCdkStack } from "../lib/blueprint_metrics_cdk-stack";

dotenv.config();

const app = new cdk.App();
new BlueprintMetricsCdkStack(app, "blueprint-metric-stack", {
  discordWebhookUrl: process.env.DISCORD_WEBHOOK_URL || "",
  githubToken: process.env.GITHUB_TOKEN || "",
  googleWorkloadIdentityAudience:
    process.env.GOOGLE_WORKLOADIDENTITY_AUDIENCE || "",
  googleWorkloadIdentityServiceAccount:
    process.env.GOOGLE_WORKLOADIDENTITY_SERVICEACCOUNT || "",
});
