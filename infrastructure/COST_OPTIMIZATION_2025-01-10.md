# Infrastructure Cost Optimization - January 10, 2025

## Summary

Successfully downsized infrastructure to **absolute minimum configuration** for small-scale production.

**Cost Reduction**: ~$310/month → ~$246/month (-21%, $64/month savings)
**Annual Savings**: $768/year

## Changes Applied

### ECS Fargate (Compute)
```
Before:
- 2 tasks minimum
- 2 vCPU, 4 GB RAM per task
- Auto-scaling: 2-10 tasks
- Cost: ~$60/month

After:
- 1 task minimum
- 1 vCPU, 2 GB RAM per task
- Auto-scaling: 1-4 tasks
- Cost: ~$37/month
- Savings: $23/month (-38%)
```

### RDS PostgreSQL (Database)
```
Before:
- Multi-AZ enabled
- Performance Insights enabled
- db.t3.medium
- Cost: ~$100/month

After:
- Single-AZ only
- Performance Insights disabled
- db.t3.medium
- Cost: ~$60/month
- Savings: $40/month (-40%)
```

### Monitoring & Features
```
Disabled:
- Container Insights (ECS monitoring)
- Performance Insights (RDS)
- Multi-AZ failover

Kept:
- CloudWatch Logs (basic)
- CloudWatch Alarms (basic)
- Auto-scaling (reduced capacity)
```

## New Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (1 task, 1 vCPU, 2GB) | $37 |
| RDS db.t3.medium (Single-AZ) | $60 |
| ElastiCache cache.t3.small | $25 |
| Application Load Balancer | $24 |
| NAT Gateways (2 required) | $80 |
| S3 + Data Transfer | $10 |
| CloudWatch Logs | $10 |
| **Total** | **~$246/month** |

## Trade-offs

### What was sacrificed:
- ❌ **No ECS redundancy**: Single task = single point of failure
- ❌ **No database failover**: Single-AZ RDS
- ❌ **Reduced capacity**: Max 4 tasks (was 10)
- ❌ **Limited monitoring**: No Performance Insights
- ❌ **Slower under load**: 1 vCPU vs 2 vCPU

### What was retained:
- ✅ **Database**: Full db.t3.medium (2 vCPU, 4 GB)
- ✅ **Redis cache**: cache.t3.small
- ✅ **Auto-scaling**: Still scales to 4 tasks under load
- ✅ **SSL/TLS**: Load balancer with certificate
- ✅ **Basic monitoring**: CloudWatch logs and alarms
- ✅ **Security**: WAF, security groups, encryption

## Suitable For

✅ **Good for:**
- Small-scale production (<5,000 documents/month)
- Development/staging environments
- Cost-sensitive deployments
- Non-critical workloads

❌ **Not suitable for:**
- High-traffic production (>10K docs/month)
- Mission-critical applications requiring 99.9% uptime
- Applications requiring instant failover
- Workloads with strict SLA requirements

## Terraform Changes

Modified file: `infrastructure/terraform/terraform.tfvars`

```hcl
# ECS Configuration
ecs_task_cpu                 = "1024"  # 1 vCPU
ecs_task_memory              = "2048"  # 2 GB
ecs_service_desired_count    = 1       # 1 task
ecs_autoscaling_min_capacity = 1       # Min 1
ecs_autoscaling_max_capacity = 4       # Max 4

# Feature Flags
enable_container_insights   = false
enable_deletion_protection  = false
enable_multi_az             = false
enable_performance_insights = false
```

## Deployment Status

✅ **Applied**: January 10, 2025 at 20:30 UTC
✅ **Resources Changed**: 1 added, 3 changed, 1 destroyed
✅ **Status**: Successfully deployed to production

## Monitoring

### Current Status
```bash
# Check ECS service
aws ecs describe-services \
  --cluster pm-doc-intel-cluster-production \
  --services pm-doc-intel-backend-service-production

# Check running tasks
aws ecs list-tasks \
  --cluster pm-doc-intel-cluster-production

# View logs
aws logs tail /ecs/pm-doc-intel/production --follow
```

### Key Metrics to Watch
- ECS task CPU utilization (should stay <80%)
- ECS task memory utilization (should stay <80%)
- Database connections (should stay <50)
- Response time P95 (should stay <2s)

### Scaling Behavior
- **Scale up**: When CPU >70% for 3 minutes
- **Scale down**: When CPU <30% for 10 minutes
- **Maximum tasks**: 4 (was 10)
- **Cooldown**: 300 seconds

## Rollback Plan

If issues arise, revert by updating terraform.tfvars:

```hcl
# Restore previous configuration
ecs_task_cpu                 = "2048"  # 2 vCPU
ecs_task_memory              = "4096"  # 4 GB
ecs_service_desired_count    = 2       # 2 tasks
ecs_autoscaling_min_capacity = 2       # Min 2
ecs_autoscaling_max_capacity = 10      # Max 10

enable_container_insights   = true
enable_multi_az             = true
enable_performance_insights = true
```

Then apply:
```bash
cd infrastructure/terraform
terraform plan -out=tfplan-rollback
terraform apply tfplan-rollback
```

## Next Steps

1. **Monitor for 48 hours**: Watch metrics, errors, response times
2. **Load test**: Verify performance under expected load
3. **Consider Reserved Instances**: If stable, purchase 1-year RI for additional 34% savings
4. **Review monthly**: Re-assess if needs change

## Related Documents

- [COST_ANALYSIS.md](../docs/COST_ANALYSIS.md) - Full cost breakdown and optimization strategies
- [DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Deployment procedures
- [terraform.tfvars](./terraform/terraform.tfvars) - Current configuration (gitignored)

---

**Last Updated**: January 10, 2025
**Applied By**: Claude Code
**Status**: Active in Production
