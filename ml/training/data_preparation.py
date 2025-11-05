"""
Data Preparation for Fine-tuning
Prepares training data from processed documents for model fine-tuning
"""

import json
import re
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.core.database import SessionLocal
from backend.app.models.document import Document, ProcessingResult
from backend.app.models.user import User
from sqlalchemy import and_, func


class PIIDetector:
    """Detect and remove PII from training data"""

    # PII patterns
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
    CREDIT_CARD_PATTERN = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'

    # Names (basic - in production use a NER model)
    COMMON_NAMES = [
        "John", "Jane", "Michael", "Sarah", "David", "Emily",
        "James", "Mary", "Robert", "Jennifer", "William", "Linda"
    ]

    @classmethod
    def remove_pii(cls, text: str) -> str:
        """
        Remove PII from text

        Args:
            text: Input text

        Returns:
            Text with PII replaced by placeholders
        """
        # Replace emails
        text = re.sub(cls.EMAIL_PATTERN, '[EMAIL]', text)

        # Replace phone numbers
        text = re.sub(cls.PHONE_PATTERN, '[PHONE]', text)

        # Replace SSNs
        text = re.sub(cls.SSN_PATTERN, '[SSN]', text)

        # Replace credit cards
        text = re.sub(cls.CREDIT_CARD_PATTERN, '[CREDIT_CARD]', text)

        # Replace common names (basic approach)
        for name in cls.COMMON_NAMES:
            pattern = r'\b' + name + r'\b'
            text = re.sub(pattern, '[NAME]', text, flags=re.IGNORECASE)

        return text

    @classmethod
    def contains_pii(cls, text: str) -> bool:
        """Check if text contains PII"""
        return bool(
            re.search(cls.EMAIL_PATTERN, text) or
            re.search(cls.PHONE_PATTERN, text) or
            re.search(cls.SSN_PATTERN, text) or
            re.search(cls.CREDIT_CARD_PATTERN, text)
        )


class TrainingDataCollector:
    """
    Collects and prepares training data from processed documents
    """

    def __init__(self, output_dir: str = "ml/data/training"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db = SessionLocal()

    def collect_document_summaries(
        self,
        min_quality_score: float = 0.8,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Collect document summarization examples

        Args:
            min_quality_score: Minimum quality score for examples
            limit: Maximum number of examples

        Returns:
            List of training examples
        """
        print(f"Collecting document summaries (min_quality={min_quality_score})...")

        examples = []

        # Query successful processing results with feedback
        results = self.db.query(ProcessingResult).join(Document).filter(
            and_(
                ProcessingResult.status == "completed",
                ProcessingResult.result_data.isnot(None)
            )
        ).limit(limit).all()

        for result in results:
            try:
                # Extract document text and summary
                doc = result.document
                result_data = result.result_data

                if not result_data or "summary" not in result_data:
                    continue

                # Get document text (first 4000 chars for context)
                doc_text = doc.extracted_text[:4000] if doc.extracted_text else ""

                if not doc_text:
                    continue

                summary = result_data.get("summary", {})

                # Remove PII
                doc_text_clean = PIIDetector.remove_pii(doc_text)

                # Skip if too much PII was detected
                if PIIDetector.contains_pii(doc_text_clean):
                    print(f"  Skipping document {doc.id} - PII detected")
                    continue

                # Calculate quality score (based on feedback if available)
                quality_score = self._calculate_quality_score(result)

                if quality_score < min_quality_score:
                    continue

                example = {
                    "id": str(result.id),
                    "document_type": doc.document_type,
                    "input": doc_text_clean,
                    "output": summary,
                    "quality_score": quality_score,
                    "created_at": result.created_at.isoformat(),
                    "metadata": {
                        "file_type": doc.file_type,
                        "page_count": doc.page_count
                    }
                }

                examples.append(example)

            except Exception as e:
                print(f"  Error processing result {result.id}: {str(e)}")
                continue

        print(f"Collected {len(examples)} summary examples")
        return examples

    def collect_action_items(
        self,
        min_quality_score: float = 0.8,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Collect action item extraction examples
        """
        print(f"Collecting action items (min_quality={min_quality_score})...")

        examples = []

        results = self.db.query(ProcessingResult).join(Document).filter(
            and_(
                ProcessingResult.status == "completed",
                ProcessingResult.result_data.isnot(None)
            )
        ).limit(limit).all()

        for result in results:
            try:
                result_data = result.result_data

                if not result_data or "action_items" not in result_data:
                    continue

                action_items = result_data.get("action_items", [])

                if not action_items:
                    continue

                doc = result.document
                doc_text = doc.extracted_text[:4000] if doc.extracted_text else ""

                if not doc_text:
                    continue

                # Remove PII
                doc_text_clean = PIIDetector.remove_pii(doc_text)

                if PIIDetector.contains_pii(doc_text_clean):
                    continue

                quality_score = self._calculate_quality_score(result)

                if quality_score < min_quality_score:
                    continue

                # Clean action items
                cleaned_items = []
                for item in action_items:
                    if isinstance(item, dict):
                        item_text = PIIDetector.remove_pii(item.get("description", ""))
                        cleaned_items.append({
                            "description": item_text,
                            "priority": item.get("priority", "medium"),
                            "due_date": item.get("due_date")
                        })

                example = {
                    "id": str(result.id),
                    "document_type": doc.document_type,
                    "input": doc_text_clean,
                    "output": cleaned_items,
                    "quality_score": quality_score,
                    "created_at": result.created_at.isoformat()
                }

                examples.append(example)

            except Exception as e:
                print(f"  Error processing result {result.id}: {str(e)}")
                continue

        print(f"Collected {len(examples)} action item examples")
        return examples

    def collect_entity_extraction(
        self,
        min_quality_score: float = 0.8,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Collect entity extraction examples
        """
        print(f"Collecting entity extractions (min_quality={min_quality_score})...")

        examples = []

        results = self.db.query(ProcessingResult).join(Document).filter(
            and_(
                ProcessingResult.status == "completed",
                ProcessingResult.result_data.isnot(None)
            )
        ).limit(limit).all()

        for result in results:
            try:
                result_data = result.result_data

                if not result_data or "entities" not in result_data:
                    continue

                entities = result_data.get("entities", {})

                if not entities:
                    continue

                doc = result.document
                doc_text = doc.extracted_text[:4000] if doc.extracted_text else ""

                if not doc_text:
                    continue

                # Remove PII from document
                doc_text_clean = PIIDetector.remove_pii(doc_text)

                # Remove PII from entities
                cleaned_entities = {}
                for entity_type, values in entities.items():
                    if entity_type in ["people", "emails", "phone_numbers"]:
                        # Skip PII entity types
                        continue
                    cleaned_entities[entity_type] = values

                if not cleaned_entities:
                    continue

                quality_score = self._calculate_quality_score(result)

                if quality_score < min_quality_score:
                    continue

                example = {
                    "id": str(result.id),
                    "document_type": doc.document_type,
                    "input": doc_text_clean,
                    "output": cleaned_entities,
                    "quality_score": quality_score,
                    "created_at": result.created_at.isoformat()
                }

                examples.append(example)

            except Exception as e:
                print(f"  Error processing result {result.id}: {str(e)}")
                continue

        print(f"Collected {len(examples)} entity extraction examples")
        return examples

    def _calculate_quality_score(self, result: ProcessingResult) -> float:
        """
        Calculate quality score based on various factors

        Factors:
        - User feedback (if available)
        - Processing success rate
        - Result completeness
        - Confidence scores
        """
        score = 0.5  # Base score

        # Check for user feedback
        result_data = result.result_data or {}
        feedback = result_data.get("feedback", {})

        if feedback.get("rating") == "positive":
            score += 0.3
        elif feedback.get("rating") == "negative":
            score -= 0.3

        # Check result completeness
        if result_data.get("summary"):
            score += 0.1
        if result_data.get("action_items"):
            score += 0.1
        if result_data.get("entities"):
            score += 0.1

        # Check confidence scores
        if "confidence" in result_data:
            confidence = result_data["confidence"]
            if isinstance(confidence, (int, float)):
                score += confidence * 0.2

        return min(1.0, max(0.0, score))

    def format_for_claude_finetuning(
        self,
        examples: List[Dict[str, Any]],
        task_type: str = "summarization"
    ) -> List[Dict[str, Any]]:
        """
        Format examples for Claude fine-tuning via AWS Bedrock

        Claude format:
        {
            "prompt": "Human: ...\n\nAssistant:",
            "completion": " ..."
        }
        """
        print(f"Formatting {len(examples)} examples for Claude fine-tuning...")

        formatted = []

        for example in examples:
            # Create prompt based on task type
            if task_type == "summarization":
                prompt = f"Human: Please provide a comprehensive summary of the following document:\n\n{example['input']}\n\nAssistant:"
                completion = f" {json.dumps(example['output'])}"

            elif task_type == "action_items":
                prompt = f"Human: Extract all action items from the following document:\n\n{example['input']}\n\nAssistant:"
                completion = f" {json.dumps(example['output'])}"

            elif task_type == "entities":
                prompt = f"Human: Extract all named entities from the following document:\n\n{example['input']}\n\nAssistant:"
                completion = f" {json.dumps(example['output'])}"

            else:
                continue

            formatted.append({
                "prompt": prompt,
                "completion": completion,
                "metadata": {
                    "id": example["id"],
                    "quality_score": example["quality_score"],
                    "document_type": example.get("document_type")
                }
            })

        return formatted

    def format_for_openai_finetuning(
        self,
        examples: List[Dict[str, Any]],
        task_type: str = "summarization"
    ) -> List[Dict[str, Any]]:
        """
        Format examples for OpenAI fine-tuning

        OpenAI format:
        {
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
        """
        print(f"Formatting {len(examples)} examples for OpenAI fine-tuning...")

        formatted = []

        for example in examples:
            system_message = self._get_system_message(task_type)

            if task_type == "summarization":
                user_content = f"Please summarize the following document:\n\n{example['input']}"
                assistant_content = json.dumps(example['output'])

            elif task_type == "action_items":
                user_content = f"Extract action items from this document:\n\n{example['input']}"
                assistant_content = json.dumps(example['output'])

            elif task_type == "entities":
                user_content = f"Extract named entities from this document:\n\n{example['input']}"
                assistant_content = json.dumps(example['output'])

            else:
                continue

            formatted.append({
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content}
                ],
                "metadata": {
                    "id": example["id"],
                    "quality_score": example["quality_score"]
                }
            })

        return formatted

    def _get_system_message(self, task_type: str) -> str:
        """Get system message for task type"""
        messages = {
            "summarization": "You are an expert at summarizing project management documents. Provide clear, concise, and actionable summaries.",
            "action_items": "You are an expert at extracting action items from documents. Identify tasks, owners, and deadlines accurately.",
            "entities": "You are an expert at named entity recognition. Extract organizations, projects, dates, and other key entities."
        }
        return messages.get(task_type, "You are a helpful AI assistant.")

    def split_dataset(
        self,
        examples: List[Dict[str, Any]],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_state: int = 42
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Split dataset into train/validation/test sets

        Args:
            examples: List of training examples
            train_ratio: Proportion for training
            val_ratio: Proportion for validation
            test_ratio: Proportion for testing
            random_state: Random seed

        Returns:
            (train_data, val_data, test_data)
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.001, "Ratios must sum to 1.0"

        # First split: train vs (val + test)
        train_data, temp_data = train_test_split(
            examples,
            test_size=(val_ratio + test_ratio),
            random_state=random_state
        )

        # Second split: val vs test
        val_size = val_ratio / (val_ratio + test_ratio)
        val_data, test_data = train_test_split(
            temp_data,
            test_size=(1 - val_size),
            random_state=random_state
        )

        print(f"\nDataset split:")
        print(f"  Train: {len(train_data)} examples ({train_ratio*100:.1f}%)")
        print(f"  Val:   {len(val_data)} examples ({val_ratio*100:.1f}%)")
        print(f"  Test:  {len(test_data)} examples ({test_ratio*100:.1f}%)")

        return train_data, val_data, test_data

    def perform_quality_checks(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform quality checks on training data

        Returns:
            Quality metrics and issues
        """
        print("\nPerforming quality checks...")

        issues = []
        stats = {
            "total_examples": len(examples),
            "avg_input_length": 0,
            "avg_output_length": 0,
            "empty_inputs": 0,
            "empty_outputs": 0,
            "duplicate_inputs": 0,
            "pii_detected": 0
        }

        input_texts = []
        input_hashes = set()

        for example in examples:
            # Check input
            input_text = example.get("input", "")
            if not input_text:
                stats["empty_inputs"] += 1
                issues.append(f"Empty input in example {example.get('id')}")
            else:
                input_texts.append(len(input_text))

                # Check for duplicates
                input_hash = hashlib.md5(input_text.encode()).hexdigest()
                if input_hash in input_hashes:
                    stats["duplicate_inputs"] += 1
                    issues.append(f"Duplicate input in example {example.get('id')}")
                input_hashes.add(input_hash)

                # Check for PII
                if PIIDetector.contains_pii(input_text):
                    stats["pii_detected"] += 1
                    issues.append(f"PII detected in example {example.get('id')}")

            # Check output
            output = example.get("output")
            if not output:
                stats["empty_outputs"] += 1
                issues.append(f"Empty output in example {example.get('id')}")
            else:
                output_str = json.dumps(output) if isinstance(output, (dict, list)) else str(output)
                input_texts.append(len(output_str))

        if input_texts:
            stats["avg_input_length"] = sum(input_texts) / len(input_texts)

        print(f"\nQuality Check Results:")
        print(f"  Total examples: {stats['total_examples']}")
        print(f"  Avg input length: {stats['avg_input_length']:.0f} chars")
        print(f"  Empty inputs: {stats['empty_inputs']}")
        print(f"  Empty outputs: {stats['empty_outputs']}")
        print(f"  Duplicate inputs: {stats['duplicate_inputs']}")
        print(f"  PII detected: {stats['pii_detected']}")
        print(f"  Total issues: {len(issues)}")

        return {
            "stats": stats,
            "issues": issues,
            "passed": len(issues) == 0
        }

    def save_dataset(
        self,
        examples: List[Dict[str, Any]],
        filename: str,
        format: str = "jsonl"
    ):
        """
        Save dataset to file

        Args:
            examples: Training examples
            filename: Output filename
            format: File format (jsonl, json, csv)
        """
        filepath = self.output_dir / filename

        print(f"\nSaving {len(examples)} examples to {filepath}...")

        if format == "jsonl":
            with open(filepath, 'w') as f:
                for example in examples:
                    f.write(json.dumps(example) + '\n')

        elif format == "json":
            with open(filepath, 'w') as f:
                json.dump(examples, f, indent=2)

        elif format == "csv":
            # Flatten examples for CSV
            flattened = []
            for ex in examples:
                flat = {
                    "id": ex.get("id"),
                    "input": ex.get("input"),
                    "output": json.dumps(ex.get("output")),
                    "quality_score": ex.get("quality_score"),
                    "document_type": ex.get("document_type")
                }
                flattened.append(flat)

            df = pd.DataFrame(flattened)
            df.to_csv(filepath, index=False)

        print(f"Saved successfully!")

    def close(self):
        """Close database connection"""
        self.db.close()


def main():
    """Main data preparation pipeline"""
    print("=" * 60)
    print("Training Data Preparation")
    print("=" * 60)
    print()

    collector = TrainingDataCollector()

    try:
        # Collect different types of training data
        print("1. Collecting summarization examples...")
        summary_examples = collector.collect_document_summaries(
            min_quality_score=0.7,
            limit=1000
        )

        print("\n2. Collecting action item examples...")
        action_examples = collector.collect_action_items(
            min_quality_score=0.7,
            limit=1000
        )

        print("\n3. Collecting entity extraction examples...")
        entity_examples = collector.collect_entity_extraction(
            min_quality_score=0.7,
            limit=1000
        )

        # Quality checks
        print("\n" + "=" * 60)
        print("Quality Checks")
        print("=" * 60)

        summary_qc = collector.perform_quality_checks(summary_examples)
        action_qc = collector.perform_quality_checks(action_examples)
        entity_qc = collector.perform_quality_checks(entity_examples)

        # Format for different platforms
        print("\n" + "=" * 60)
        print("Formatting for Fine-tuning Platforms")
        print("=" * 60)

        # Claude format
        claude_summaries = collector.format_for_claude_finetuning(
            summary_examples, "summarization"
        )

        # OpenAI format
        openai_summaries = collector.format_for_openai_finetuning(
            summary_examples, "summarization"
        )

        # Split datasets
        print("\n" + "=" * 60)
        print("Splitting Datasets")
        print("=" * 60)

        sum_train, sum_val, sum_test = collector.split_dataset(claude_summaries)
        act_train, act_val, act_test = collector.split_dataset(action_examples)

        # Save datasets
        print("\n" + "=" * 60)
        print("Saving Datasets")
        print("=" * 60)

        collector.save_dataset(sum_train, "summaries_train.jsonl", "jsonl")
        collector.save_dataset(sum_val, "summaries_val.jsonl", "jsonl")
        collector.save_dataset(sum_test, "summaries_test.jsonl", "jsonl")

        collector.save_dataset(act_train, "actions_train.jsonl", "jsonl")
        collector.save_dataset(act_val, "actions_val.jsonl", "jsonl")
        collector.save_dataset(act_test, "actions_test.jsonl", "jsonl")

        # Save OpenAI format
        collector.save_dataset(openai_summaries, "openai_summaries.jsonl", "jsonl")

        print("\n" + "=" * 60)
        print("Data Preparation Complete!")
        print("=" * 60)
        print(f"\nFiles saved to: {collector.output_dir}")
        print("\nNext steps:")
        print("1. Review the generated datasets")
        print("2. Run fine-tuning with ml/training/fine_tuning.py")
        print("3. Evaluate model performance")

    finally:
        collector.close()


if __name__ == "__main__":
    main()
