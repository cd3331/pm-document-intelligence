"""
Model Fine-tuning
Fine-tune Claude via AWS Bedrock and OpenAI models
"""

import json
import boto3
import openai
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.core.config import settings


class ClaudeFineTuner:
    """
    Fine-tune Claude models via AWS Bedrock Custom Model Import
    """

    def __init__(self):
        self.bedrock = boto3.client(
            'bedrock',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

        self.s3 = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

        self.bucket_name = settings.S3_BUCKET_NAME

    def upload_training_data(self, data_file: str, s3_key: str) -> str:
        """
        Upload training data to S3

        Args:
            data_file: Local path to training data
            s3_key: S3 object key

        Returns:
            S3 URI
        """
        print(f"Uploading {data_file} to S3...")

        self.s3.upload_file(
            data_file,
            self.bucket_name,
            s3_key
        )

        s3_uri = f"s3://{self.bucket_name}/{s3_key}"
        print(f"Uploaded to {s3_uri}")

        return s3_uri

    def create_finetuning_job(
        self,
        job_name: str,
        base_model_id: str,
        training_data_uri: str,
        validation_data_uri: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a fine-tuning job in AWS Bedrock

        Args:
            job_name: Name for the job
            base_model_id: Base model identifier (e.g., 'anthropic.claude-v2')
            training_data_uri: S3 URI for training data
            validation_data_uri: Optional S3 URI for validation data
            hyperparameters: Training hyperparameters

        Returns:
            Job details
        """
        print(f"\nCreating fine-tuning job: {job_name}")
        print(f"Base model: {base_model_id}")

        # Default hyperparameters
        if hyperparameters is None:
            hyperparameters = {
                "epochCount": "3",
                "batchSize": "4",
                "learningRate": "0.00001",
                "learningRateWarmupSteps": "100"
            }

        job_config = {
            "modelName": job_name,
            "baseModelIdentifier": base_model_id,
            "trainingDataConfig": {
                "s3Uri": training_data_uri
            },
            "hyperParameters": hyperparameters,
            "outputDataConfig": {
                "s3Uri": f"s3://{self.bucket_name}/models/{job_name}"
            }
        }

        if validation_data_uri:
            job_config["validationDataConfig"] = {
                "s3Uri": validation_data_uri
            }

        try:
            response = self.bedrock.create_model_customization_job(**job_config)

            print(f"Job created: {response['jobArn']}")

            return {
                "job_arn": response['jobArn'],
                "job_name": job_name,
                "status": "InProgress",
                "created_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error creating job: {str(e)}")
            raise

    def get_job_status(self, job_arn: str) -> Dict[str, Any]:
        """
        Get status of a fine-tuning job

        Args:
            job_arn: Job ARN

        Returns:
            Job status and metrics
        """
        try:
            response = self.bedrock.get_model_customization_job(
                jobIdentifier=job_arn
            )

            return {
                "status": response['status'],
                "job_name": response.get('jobName'),
                "base_model": response.get('baseModelArn'),
                "training_metrics": response.get('trainingMetrics', {}),
                "validation_metrics": response.get('validationMetrics', {}),
                "output_model_arn": response.get('outputModelArn'),
                "failure_reason": response.get('failureMessage')
            }

        except Exception as e:
            print(f"Error getting job status: {str(e)}")
            raise

    def wait_for_completion(
        self,
        job_arn: str,
        check_interval: int = 300,
        max_wait: int = 7200
    ) -> Dict[str, Any]:
        """
        Wait for fine-tuning job to complete

        Args:
            job_arn: Job ARN
            check_interval: Seconds between checks
            max_wait: Maximum wait time in seconds

        Returns:
            Final job status
        """
        print(f"\nWaiting for job completion...")
        print(f"Job ARN: {job_arn}")
        print(f"Check interval: {check_interval}s")

        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Job did not complete within {max_wait}s")

            status = self.get_job_status(job_arn)

            print(f"Status: {status['status']}")

            if status['status'] == 'Completed':
                print("Job completed successfully!")
                return status

            elif status['status'] in ['Failed', 'Stopped']:
                print(f"Job failed: {status.get('failure_reason')}")
                return status

            time.sleep(check_interval)

    def deploy_model(self, model_arn: str, provisioned_throughput: int = 100) -> Dict[str, Any]:
        """
        Deploy fine-tuned model with provisioned throughput

        Args:
            model_arn: ARN of fine-tuned model
            provisioned_throughput: Provisioned throughput units

        Returns:
            Deployment details
        """
        print(f"\nDeploying model: {model_arn}")

        try:
            response = self.bedrock.create_provisioned_model_throughput(
                modelId=model_arn,
                provisionedModelName=f"deployed-{model_arn.split('/')[-1]}",
                modelUnits=provisioned_throughput
            )

            return {
                "provisioned_model_arn": response['provisionedModelArn'],
                "status": "Creating"
            }

        except Exception as e:
            print(f"Error deploying model: {str(e)}")
            raise


class OpenAIFineTuner:
    """
    Fine-tune OpenAI models for embeddings and completion
    """

    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    def upload_training_file(self, file_path: str, purpose: str = "fine-tune") -> str:
        """
        Upload training file to OpenAI

        Args:
            file_path: Path to training data file (JSONL format)
            purpose: Purpose of file ('fine-tune')

        Returns:
            File ID
        """
        print(f"Uploading {file_path} to OpenAI...")

        with open(file_path, 'rb') as f:
            response = openai.File.create(
                file=f,
                purpose=purpose
            )

        file_id = response['id']
        print(f"File uploaded: {file_id}")

        return file_id

    def create_finetuning_job(
        self,
        training_file_id: str,
        model: str = "gpt-3.5-turbo",
        validation_file_id: Optional[str] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create fine-tuning job with OpenAI

        Args:
            training_file_id: Training file ID
            model: Base model ('gpt-3.5-turbo', 'davinci-002', 'babbage-002')
            validation_file_id: Optional validation file ID
            hyperparameters: Training hyperparameters
            suffix: Optional suffix for fine-tuned model name

        Returns:
            Job details
        """
        print(f"\nCreating OpenAI fine-tuning job")
        print(f"Base model: {model}")
        print(f"Training file: {training_file_id}")

        job_params = {
            "training_file": training_file_id,
            "model": model
        }

        if validation_file_id:
            job_params["validation_file"] = validation_file_id

        if hyperparameters:
            job_params["hyperparameters"] = hyperparameters

        if suffix:
            job_params["suffix"] = suffix

        response = openai.FineTuningJob.create(**job_params)

        print(f"Job created: {response['id']}")

        return {
            "job_id": response['id'],
            "model": response['model'],
            "status": response['status'],
            "created_at": response['created_at']
        }

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get fine-tuning job status

        Args:
            job_id: Job ID

        Returns:
            Job status and metrics
        """
        response = openai.FineTuningJob.retrieve(job_id)

        return {
            "job_id": response['id'],
            "status": response['status'],
            "model": response['model'],
            "fine_tuned_model": response.get('fine_tuned_model'),
            "trained_tokens": response.get('trained_tokens'),
            "created_at": response['created_at'],
            "finished_at": response.get('finished_at'),
            "error": response.get('error')
        }

    def list_job_events(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List events for a fine-tuning job

        Args:
            job_id: Job ID
            limit: Maximum events to return

        Returns:
            List of events
        """
        response = openai.FineTuningJob.list_events(
            job_id,
            limit=limit
        )

        return [
            {
                "message": event['message'],
                "level": event['level'],
                "created_at": event['created_at']
            }
            for event in response['data']
        ]

    def wait_for_completion(
        self,
        job_id: str,
        check_interval: int = 60,
        max_wait: int = 3600
    ) -> Dict[str, Any]:
        """
        Wait for fine-tuning job to complete

        Args:
            job_id: Job ID
            check_interval: Seconds between checks
            max_wait: Maximum wait time

        Returns:
            Final job status
        """
        print(f"\nWaiting for OpenAI job completion...")
        print(f"Job ID: {job_id}")

        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Job did not complete within {max_wait}s")

            status = self.get_job_status(job_id)

            print(f"Status: {status['status']}")

            if status['status'] == 'succeeded':
                print(f"Job completed! Model: {status['fine_tuned_model']}")
                return status

            elif status['status'] in ['failed', 'cancelled']:
                print(f"Job failed: {status.get('error')}")
                return status

            time.sleep(check_interval)

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a fine-tuning job"""
        response = openai.FineTuningJob.cancel(job_id)
        return {"job_id": response['id'], "status": response['status']}


class HyperparameterOptimizer:
    """
    Optimize hyperparameters for fine-tuning
    """

    @staticmethod
    def grid_search_params() -> List[Dict[str, Any]]:
        """
        Generate hyperparameter grid for search

        Returns:
            List of hyperparameter combinations
        """
        learning_rates = [0.00001, 0.00005, 0.0001]
        batch_sizes = [4, 8, 16]
        epochs = [2, 3, 4]

        params = []
        for lr in learning_rates:
            for bs in batch_sizes:
                for ep in epochs:
                    params.append({
                        "learning_rate": lr,
                        "batch_size": bs,
                        "epochs": ep
                    })

        return params

    @staticmethod
    def optimize_for_openai(
        training_data_size: int
    ) -> Dict[str, Any]:
        """
        Suggest optimal hyperparameters for OpenAI based on dataset size

        Args:
            training_data_size: Number of training examples

        Returns:
            Suggested hyperparameters
        """
        # Rules of thumb
        if training_data_size < 100:
            return {
                "n_epochs": 4,
                "learning_rate_multiplier": 2.0
            }
        elif training_data_size < 1000:
            return {
                "n_epochs": 3,
                "learning_rate_multiplier": 1.5
            }
        else:
            return {
                "n_epochs": 2,
                "learning_rate_multiplier": 1.0
            }


def run_claude_finetuning(
    training_file: str,
    validation_file: Optional[str] = None,
    job_name: Optional[str] = None,
    wait: bool = True
) -> Dict[str, Any]:
    """
    Run complete Claude fine-tuning pipeline

    Args:
        training_file: Path to training data
        validation_file: Optional validation data path
        job_name: Custom job name
        wait: Wait for completion

    Returns:
        Job results
    """
    if job_name is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        job_name = f"claude_ft_{timestamp}"

    tuner = ClaudeFineTuner()

    # Upload data
    train_uri = tuner.upload_training_data(
        training_file,
        f"training/{job_name}/train.jsonl"
    )

    val_uri = None
    if validation_file:
        val_uri = tuner.upload_training_data(
            validation_file,
            f"training/{job_name}/val.jsonl"
        )

    # Create job
    job = tuner.create_finetuning_job(
        job_name=job_name,
        base_model_id="anthropic.claude-v2",
        training_data_uri=train_uri,
        validation_data_uri=val_uri
    )

    # Wait for completion
    if wait:
        result = tuner.wait_for_completion(job['job_arn'])
        return result
    else:
        return job


def run_openai_finetuning(
    training_file: str,
    model: str = "gpt-3.5-turbo",
    validation_file: Optional[str] = None,
    suffix: Optional[str] = None,
    wait: bool = True
) -> Dict[str, Any]:
    """
    Run complete OpenAI fine-tuning pipeline

    Args:
        training_file: Path to training data
        model: Base model
        validation_file: Optional validation data path
        suffix: Model name suffix
        wait: Wait for completion

    Returns:
        Job results
    """
    tuner = OpenAIFineTuner()

    # Upload training file
    train_file_id = tuner.upload_training_file(training_file)

    # Upload validation file if provided
    val_file_id = None
    if validation_file:
        val_file_id = tuner.upload_training_file(validation_file)

    # Optimize hyperparameters based on file size
    with open(training_file) as f:
        data_size = sum(1 for _ in f)

    hyperparams = HyperparameterOptimizer.optimize_for_openai(data_size)

    # Create job
    job = tuner.create_finetuning_job(
        training_file_id=train_file_id,
        model=model,
        validation_file_id=val_file_id,
        hyperparameters=hyperparams,
        suffix=suffix
    )

    # Wait for completion
    if wait:
        result = tuner.wait_for_completion(job['job_id'])
        return result
    else:
        return job


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Fine-tune AI models')
    parser.add_argument('--platform', choices=['claude', 'openai'], required=True)
    parser.add_argument('--train', required=True, help='Training data file')
    parser.add_argument('--val', help='Validation data file')
    parser.add_argument('--model', default='gpt-3.5-turbo', help='Base model (OpenAI only)')
    parser.add_argument('--name', help='Job name')
    parser.add_argument('--no-wait', action='store_true', help='Don\'t wait for completion')

    args = parser.parse_args()

    if args.platform == 'claude':
        result = run_claude_finetuning(
            args.train,
            args.val,
            args.name,
            not args.no_wait
        )
    else:
        result = run_openai_finetuning(
            args.train,
            args.model,
            args.val,
            args.name,
            not args.no_wait
        )

    print("\nFine-tuning complete!")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
