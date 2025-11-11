#!/bin/bash
# Run database migration via ECS task

set -e

echo "=================================================="
echo "Running Database Migration for Processing Columns"
echo "=================================================="

# Get the cluster and task definition
CLUSTER="pm-doc-intel-cluster-production"
TASK_DEF="pm-doc-intel-backend-production"

# Get a running task
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER --service-name pm-doc-intel-backend-service-production --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" == "None" ] || [ -z "$TASK_ARN" ]; then
    echo "Error: No running tasks found"
    exit 1
fi

echo "Found running task: $TASK_ARN"
echo ""
echo "Executing migration commands..."
echo ""

# Execute the migration SQL commands via the running container
aws ecs execute-command \
    --cluster $CLUSTER \
    --task $(basename $TASK_ARN) \
    --container backend \
    --interactive \
    --command "/bin/bash -c 'python -c \"
import asyncio
from app.database import get_db_session
from sqlalchemy import text

async def migrate():
    async with get_db_session() as session:
        # Add missing columns
        await session.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB'))
        await session.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB'))
        await session.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT'))
        await session.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT \\\'[]\\\'::jsonb'))
        await session.execute(text('ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT \\\'{}\\\'::jsonb'))
        await session.commit()
        print('Migration completed successfully!')

asyncio.run(migrate())
\"'"

echo ""
echo "=================================================="
echo "Migration completed!"
echo "=================================================="
