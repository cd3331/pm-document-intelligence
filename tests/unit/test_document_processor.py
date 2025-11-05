"""
Unit tests for document processing module
Tests text extraction, entity extraction, and action item parsing
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from app.services.document_processor import DocumentProcessor
from app.models import Document


@pytest.mark.unit
class TestTextExtraction:
    """Test text extraction from various document formats"""

    @pytest.mark.aws
    def test_extract_text_from_pdf(
        self,
        mock_aws_services,
        sample_pdf_file: Path
    ):
        """Test extracting text from PDF using Textract"""
        processor = DocumentProcessor()

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['textract']

            text = processor.extract_text_from_pdf(str(sample_pdf_file))

            assert text is not None
            assert len(text) > 0
            assert "extracted text" in text.lower()

    def test_extract_text_from_txt(self, sample_txt_file: Path):
        """Test extracting text from plain text file"""
        processor = DocumentProcessor()

        text = processor.extract_text_from_txt(str(sample_txt_file))

        assert text is not None
        assert "test document" in text.lower()
        assert "action item" in text.lower()

    @pytest.mark.aws
    def test_extract_text_from_docx(self, mock_aws_services):
        """Test extracting text from DOCX file"""
        processor = DocumentProcessor()

        # Mock docx extraction
        with patch('docx.Document') as mock_docx:
            mock_doc = MagicMock()
            mock_paragraph = MagicMock()
            mock_paragraph.text = "This is DOCX text"
            mock_doc.paragraphs = [mock_paragraph]
            mock_docx.return_value = mock_doc

            text = processor.extract_text_from_docx("test.docx")

            assert text is not None
            assert "docx text" in text.lower()

    def test_extract_text_unsupported_format(self):
        """Test extraction with unsupported file format"""
        processor = DocumentProcessor()

        with pytest.raises(ValueError, match="Unsupported"):
            processor.extract_text("unsupported.xyz")

    def test_extract_text_missing_file(self):
        """Test extraction with missing file"""
        processor = DocumentProcessor()

        with pytest.raises(FileNotFoundError):
            processor.extract_text_from_pdf("/nonexistent/file.pdf")

    @pytest.mark.aws
    def test_extract_text_textract_error(self, mock_aws_services):
        """Test handling Textract errors"""
        processor = DocumentProcessor()

        mock_textract = mock_aws_services['textract']
        mock_textract.detect_document_text.side_effect = Exception("Textract error")

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_textract

            with pytest.raises(Exception, match="Textract error"):
                processor.extract_text_from_pdf("test.pdf")


@pytest.mark.unit
class TestEntityExtraction:
    """Test entity extraction using AWS Comprehend"""

    @pytest.mark.aws
    def test_extract_entities_success(self, mock_aws_services):
        """Test successful entity extraction"""
        processor = DocumentProcessor()

        text = "John Doe works at Acme Corp and has a meeting on Friday."

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['comprehend']

            entities = processor.extract_entities(text)

            assert entities is not None
            assert len(entities) > 0
            assert any(e['Type'] == 'PERSON' for e in entities)
            assert any(e['Type'] == 'ORGANIZATION' for e in entities)

    @pytest.mark.aws
    def test_extract_entities_empty_text(self, mock_aws_services):
        """Test entity extraction with empty text"""
        processor = DocumentProcessor()

        entities = processor.extract_entities("")

        assert entities == []

    @pytest.mark.aws
    def test_extract_entities_long_text(self, mock_aws_services):
        """Test entity extraction with text exceeding Comprehend limit"""
        processor = DocumentProcessor()

        # Create text longer than Comprehend limit (5000 bytes)
        long_text = "Sample text. " * 500

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['comprehend']

            entities = processor.extract_entities(long_text)

            # Should truncate and still process
            assert isinstance(entities, list)

    @pytest.mark.aws
    def test_extract_sentiment(self, mock_aws_services):
        """Test sentiment detection"""
        processor = DocumentProcessor()

        text = "This is a great document with positive insights!"

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['comprehend']

            sentiment = processor.extract_sentiment(text)

            assert sentiment is not None
            assert 'Sentiment' in sentiment
            assert sentiment['Sentiment'] in ['POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED']

    @pytest.mark.aws
    def test_extract_key_phrases(self, mock_aws_services):
        """Test key phrase extraction"""
        processor = DocumentProcessor()

        text = "The comprehensive testing suite includes unit and integration tests."

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['comprehend']

            key_phrases = processor.extract_key_phrases(text)

            assert key_phrases is not None
            assert len(key_phrases) > 0
            assert all('Text' in phrase for phrase in key_phrases)


@pytest.mark.unit
class TestActionItemParsing:
    """Test action item extraction from text"""

    def test_parse_action_items_basic(self):
        """Test parsing basic action items"""
        processor = DocumentProcessor()

        text = """
        Action Item: Complete the testing suite by Friday.
        TODO: Review documentation before deployment.
        Task: Update dependencies to latest versions.
        """

        action_items = processor.parse_action_items(text)

        assert len(action_items) >= 3
        assert any("testing suite" in item['title'].lower() for item in action_items)
        assert any("documentation" in item['title'].lower() for item in action_items)

    def test_parse_action_items_with_assignees(self):
        """Test parsing action items with assignees"""
        processor = DocumentProcessor()

        text = """
        Action Item: @john Complete the API integration
        TODO: @sarah Review pull request #123
        """

        action_items = processor.parse_action_items(text)

        assert len(action_items) >= 2
        # Check if assignees are extracted
        assignees = [item.get('assignee') for item in action_items if item.get('assignee')]
        assert any(assignee for assignee in assignees)

    def test_parse_action_items_with_dates(self):
        """Test parsing action items with due dates"""
        processor = DocumentProcessor()

        text = """
        Action Item: Deploy to production by Friday, Dec 15
        TODO: Schedule meeting for next Monday
        Task: Complete by end of month
        """

        action_items = processor.parse_action_items(text)

        assert len(action_items) >= 2
        # Some items should have due dates extracted
        dates = [item.get('due_date') for item in action_items if item.get('due_date')]
        assert len(dates) > 0

    def test_parse_action_items_with_priority(self):
        """Test parsing action items with priority markers"""
        processor = DocumentProcessor()

        text = """
        URGENT: Fix production bug immediately
        HIGH PRIORITY: Complete security review
        Action Item: Update documentation (low priority)
        """

        action_items = processor.parse_action_items(text)

        assert len(action_items) >= 3

        # Check priority assignment
        high_priority_items = [
            item for item in action_items
            if item.get('priority') == 'high'
        ]
        assert len(high_priority_items) > 0

    def test_parse_action_items_no_items(self):
        """Test parsing text with no action items"""
        processor = DocumentProcessor()

        text = "This is just regular text with no action items."

        action_items = processor.parse_action_items(text)

        assert len(action_items) == 0

    def test_parse_action_items_with_context(self):
        """Test parsing action items with surrounding context"""
        processor = DocumentProcessor()

        text = """
        In the meeting, we discussed several important points:
        1. Action Item: Implement user authentication
        2. Follow up with stakeholders about requirements
        3. TODO: Schedule next sprint planning

        The team agreed on these deliverables.
        """

        action_items = processor.parse_action_items(text)

        assert len(action_items) >= 2
        assert any("authentication" in item['title'].lower() for item in action_items)


@pytest.mark.unit
class TestDocumentProcessing:
    """Test complete document processing workflow"""

    @pytest.mark.aws
    def test_process_document_complete_workflow(
        self,
        mock_aws_services,
        sample_pdf_file: Path,
        test_db,
        test_user
    ):
        """Test complete document processing from upload to analysis"""
        processor = DocumentProcessor()

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            def get_client(service_name, **kwargs):
                return mock_aws_services.get(service_name)

            mock_boto.side_effect = get_client

            # Create document record
            document = Document(
                filename=sample_pdf_file.name,
                s3_key=f"documents/{sample_pdf_file.name}",
                user_id=test_user.id,
                document_type="general",
                status="processing"
            )
            test_db.add(document)
            test_db.commit()

            # Process document
            result = processor.process_document(
                document_id=document.id,
                file_path=str(sample_pdf_file),
                db=test_db
            )

            assert result is not None
            assert result['status'] == 'completed'
            assert 'extracted_text' in result
            assert 'entities' in result
            assert 'sentiment' in result

    @pytest.mark.aws
    def test_process_document_with_error_handling(
        self,
        mock_aws_services,
        test_db,
        test_user
    ):
        """Test document processing error handling"""
        processor = DocumentProcessor()

        # Create document with non-existent file
        document = Document(
            filename="nonexistent.pdf",
            s3_key="documents/nonexistent.pdf",
            user_id=test_user.id,
            document_type="general",
            status="processing"
        )
        test_db.add(document)
        test_db.commit()

        with pytest.raises(Exception):
            processor.process_document(
                document_id=document.id,
                file_path="/nonexistent/file.pdf",
                db=test_db
            )

        # Check document status updated to failed
        test_db.refresh(document)
        assert document.status == "failed"

    def test_calculate_processing_cost(self):
        """Test processing cost calculation"""
        processor = DocumentProcessor()

        # Mock usage data
        usage = {
            'textract_pages': 5,
            'comprehend_units': 3,
            'bedrock_input_tokens': 1000,
            'bedrock_output_tokens': 500
        }

        cost = processor.calculate_cost(usage)

        assert cost > 0
        assert isinstance(cost, (int, float))

    def test_extract_metadata(self, sample_pdf_file: Path):
        """Test extracting document metadata"""
        processor = DocumentProcessor()

        metadata = processor.extract_metadata(str(sample_pdf_file))

        assert metadata is not None
        assert 'file_size' in metadata
        assert 'file_type' in metadata
        assert metadata['file_type'] == 'pdf'


@pytest.mark.unit
class TestDocumentValidation:
    """Test document validation"""

    def test_validate_file_type_pdf(self):
        """Test validating PDF file type"""
        processor = DocumentProcessor()

        is_valid = processor.validate_file_type("document.pdf", allowed_types=['pdf', 'docx'])

        assert is_valid is True

    def test_validate_file_type_invalid(self):
        """Test validating invalid file type"""
        processor = DocumentProcessor()

        is_valid = processor.validate_file_type("document.exe", allowed_types=['pdf', 'docx'])

        assert is_valid is False

    def test_validate_file_size_within_limit(self):
        """Test validating file size within limit"""
        processor = DocumentProcessor()

        is_valid = processor.validate_file_size(5 * 1024 * 1024, max_size=10 * 1024 * 1024)

        assert is_valid is True

    def test_validate_file_size_exceeds_limit(self):
        """Test validating file size exceeding limit"""
        processor = DocumentProcessor()

        is_valid = processor.validate_file_size(15 * 1024 * 1024, max_size=10 * 1024 * 1024)

        assert is_valid is False

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        processor = DocumentProcessor()

        unsafe_filename = "../../../etc/passwd"
        safe_filename = processor.sanitize_filename(unsafe_filename)

        assert ".." not in safe_filename
        assert "/" not in safe_filename

    def test_detect_malicious_content(self, sample_txt_file: Path):
        """Test detecting potentially malicious content"""
        processor = DocumentProcessor()

        # Create file with suspicious content
        with open(sample_txt_file, 'w') as f:
            f.write("<script>alert('xss')</script>")

        is_safe = processor.scan_for_malicious_content(str(sample_txt_file))

        # Should detect script tags
        assert is_safe is False or "suspicious" in str(is_safe).lower()


@pytest.mark.unit
class TestS3Integration:
    """Test S3 upload and download operations"""

    @pytest.mark.aws
    def test_upload_to_s3(self, mock_aws_services, sample_pdf_file: Path):
        """Test uploading file to S3"""
        processor = DocumentProcessor()

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['s3']

            s3_key = processor.upload_to_s3(
                file_path=str(sample_pdf_file),
                bucket="test-bucket",
                key="documents/test.pdf"
            )

            assert s3_key is not None
            assert "documents/test.pdf" in s3_key

    @pytest.mark.aws
    def test_download_from_s3(self, mock_aws_services):
        """Test downloading file from S3"""
        processor = DocumentProcessor()

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['s3']

            content = processor.download_from_s3(
                bucket="test-bucket",
                key="documents/test.pdf"
            )

            assert content is not None
            assert len(content) > 0

    @pytest.mark.aws
    def test_delete_from_s3(self, mock_aws_services):
        """Test deleting file from S3"""
        processor = DocumentProcessor()

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['s3']

            result = processor.delete_from_s3(
                bucket="test-bucket",
                key="documents/test.pdf"
            )

            assert result is True

    @pytest.mark.aws
    def test_generate_presigned_url(self, mock_aws_services):
        """Test generating presigned URL for S3 object"""
        processor = DocumentProcessor()

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['s3']

            url = processor.generate_presigned_url(
                bucket="test-bucket",
                key="documents/test.pdf",
                expiration=3600
            )

            assert url is not None
            assert url.startswith("https://")
            assert "test-bucket" in url or "test-key" in url


@pytest.mark.unit
class TestBatchProcessing:
    """Test batch document processing"""

    @pytest.mark.slow
    @pytest.mark.aws
    def test_process_multiple_documents(
        self,
        mock_aws_services,
        test_db,
        test_user,
        generate_documents
    ):
        """Test processing multiple documents in batch"""
        processor = DocumentProcessor()

        # Generate test documents
        documents = generate_documents(count=5, user=test_user)

        with patch('app.services.document_processor.boto3.client') as mock_boto:
            def get_client(service_name, **kwargs):
                return mock_aws_services.get(service_name)

            mock_boto.side_effect = get_client

            results = processor.process_batch(
                document_ids=[d.id for d in documents],
                db=test_db
            )

            assert len(results) == 5
            assert all('status' in result for result in results)

    def test_batch_processing_with_failures(
        self,
        test_db,
        test_user,
        generate_documents
    ):
        """Test batch processing with some failures"""
        processor = DocumentProcessor()

        documents = generate_documents(count=3, user=test_user)

        # Mock processing to fail for second document
        def mock_process(doc_id, **kwargs):
            if doc_id == documents[1].id:
                raise Exception("Processing failed")
            return {'status': 'completed', 'document_id': doc_id}

        with patch.object(processor, 'process_document', side_effect=mock_process):
            results = processor.process_batch(
                document_ids=[d.id for d in documents],
                db=test_db,
                continue_on_error=True
            )

            # Should have results for all docs, with one failed
            assert len(results) == 3
            failed = [r for r in results if r.get('status') == 'failed']
            assert len(failed) == 1
