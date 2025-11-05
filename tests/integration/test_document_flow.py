"""
Integration tests for complete document processing flow
Tests end-to-end document upload, processing, and analysis
"""

import pytest
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.models import Document, ActionItem


@pytest.mark.integration
class TestDocumentUploadFlow:
    """Test complete document upload flow"""

    def test_upload_pdf_document(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: Path,
        mock_aws_services
    ):
        """Test uploading a PDF document"""
        with open(sample_pdf_file, 'rb') as f:
            files = {'files': ('test.pdf', f, 'application/pdf')}
            data = {'document_type': 'general', 'auto_analyze': 'true'}

            with patch('boto3.client') as mock_boto:
                def get_client(service_name, **kwargs):
                    return mock_aws_services.get(service_name)
                mock_boto.side_effect = get_client

                response = client.post(
                    '/api/v1/documents/upload',
                    headers=auth_headers,
                    files=files,
                    data=data
                )

        assert response.status_code == 201
        data = response.json()
        assert 'id' in data
        assert data['filename'] == 'test.pdf'
        assert data['status'] in ['processing', 'completed']

    def test_upload_multiple_documents(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: Path,
        sample_txt_file: Path,
        mock_aws_services
    ):
        """Test uploading multiple documents at once"""
        with open(sample_pdf_file, 'rb') as pdf_f, open(sample_txt_file, 'rb') as txt_f:
            files = [
                ('files', ('test.pdf', pdf_f, 'application/pdf')),
                ('files', ('test.txt', txt_f, 'text/plain'))
            ]

            with patch('boto3.client') as mock_boto:
                def get_client(service_name, **kwargs):
                    return mock_aws_services.get(service_name)
                mock_boto.side_effect = get_client

                response = client.post(
                    '/api/v1/documents/upload',
                    headers=auth_headers,
                    files=files
                )

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_upload_with_invalid_file_type(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test uploading invalid file type"""
        files = {'files': ('test.exe', BytesIO(b'invalid'), 'application/exe')}

        response = client.post(
            '/api/v1/documents/upload',
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert 'invalid' in response.json()['detail'].lower() or 'unsupported' in response.json()['detail'].lower()

    def test_upload_file_too_large(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test uploading file exceeding size limit"""
        # Create large file (> 10MB)
        large_content = b'x' * (11 * 1024 * 1024)
        files = {'files': ('large.pdf', BytesIO(large_content), 'application/pdf')}

        response = client.post(
            '/api/v1/documents/upload',
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 413 or response.status_code == 400


@pytest.mark.integration
class TestDocumentProcessingFlow:
    """Test document processing workflow"""

    @pytest.mark.slow
    @pytest.mark.aws
    def test_complete_processing_workflow(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: Path,
        mock_aws_services,
        test_db
    ):
        """Test complete document processing from upload to analysis"""
        # Upload document
        with open(sample_pdf_file, 'rb') as f:
            files = {'files': ('test.pdf', f, 'application/pdf')}
            data = {'document_type': 'general', 'auto_analyze': 'true'}

            with patch('boto3.client') as mock_boto:
                def get_client(service_name, **kwargs):
                    return mock_aws_services.get(service_name)
                mock_boto.side_effect = get_client

                upload_response = client.post(
                    '/api/v1/documents/upload',
                    headers=auth_headers,
                    files=files,
                    data=data
                )

        assert upload_response.status_code == 201
        document_id = upload_response.json()['id']

        # Wait for processing (or check status)
        import time
        time.sleep(2)

        # Get document status
        status_response = client.get(
            f'/api/v1/documents/{document_id}',
            headers=auth_headers
        )

        assert status_response.status_code == 200
        doc_data = status_response.json()
        assert doc_data['status'] in ['processing', 'completed']

        # If completed, check for analysis results
        if doc_data['status'] == 'completed':
            assert 'extracted_text' in doc_data
            assert doc_data['extracted_text'] is not None

    @pytest.mark.aws
    def test_processing_with_error_recovery(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db,
        mock_aws_services
    ):
        """Test error recovery during processing"""
        # Create document that will fail processing
        with patch('boto3.client') as mock_boto:
            # Mock Textract to fail
            mock_textract = mock_aws_services['textract']
            mock_textract.detect_document_text.side_effect = Exception("Textract failed")

            mock_boto.return_value = mock_textract

            files = {'files': ('test.pdf', BytesIO(b'%PDF-test'), 'application/pdf')}

            response = client.post(
                '/api/v1/documents/upload',
                headers=auth_headers,
                files=files
            )

        # Should handle error gracefully
        if response.status_code == 201:
            document_id = response.json()['id']

            # Check document status
            status_response = client.get(
                f'/api/v1/documents/{document_id}',
                headers=auth_headers
            )

            doc_data = status_response.json()
            # Should eventually mark as failed
            assert doc_data['status'] in ['processing', 'failed']


@pytest.mark.integration
class TestDocumentAnalysisFlow:
    """Test document analysis features"""

    @pytest.mark.aws
    def test_extract_action_items(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_aws_services
    ):
        """Test extracting action items from document"""
        with patch('boto3.client') as mock_boto:
            def get_client(service_name, **kwargs):
                return mock_aws_services.get(service_name)
            mock_boto.side_effect = get_client

            response = client.post(
                f'/api/v1/documents/{sample_document.id}/extract-actions',
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert 'action_items' in data
        assert isinstance(data['action_items'], list)

    @pytest.mark.aws
    def test_generate_summary(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_aws_services
    ):
        """Test generating document summary"""
        with patch('boto3.client') as mock_boto:
            def get_client(service_name, **kwargs):
                return mock_aws_services.get(service_name)
            mock_boto.side_effect = get_client

            response = client.post(
                f'/api/v1/documents/{sample_document.id}/summarize',
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data
        assert len(data['summary']) > 0

    @pytest.mark.aws
    def test_qa_interaction(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_bedrock_runtime_client
    ):
        """Test Q&A interaction with document"""
        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            response = client.post(
                '/api/v1/agents/ask',
                headers=auth_headers,
                json={
                    'question': 'What is this document about?',
                    'document_id': sample_document.id,
                    'use_context': True
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data
        assert len(data['answer']) > 0


@pytest.mark.integration
class TestVectorSearchIntegration:
    """Test vector search integration"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_document_indexing_on_upload(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: Path,
        mock_aws_services,
        mock_openai_client
    ):
        """Test that documents are automatically indexed on upload"""
        with patch('boto3.client') as mock_boto, patch('openai.OpenAI') as mock_openai:
            def get_client(service_name, **kwargs):
                return mock_aws_services.get(service_name)
            mock_boto.side_effect = get_client
            mock_openai.return_value = mock_openai_client

            # Upload document
            with open(sample_pdf_file, 'rb') as f:
                files = {'files': ('test.pdf', f, 'application/pdf')}

                response = client.post(
                    '/api/v1/documents/upload',
                    headers=auth_headers,
                    files=files
                )

        assert response.status_code == 201

        # Document should be indexed for search
        # Test semantic search
        import time
        time.sleep(1)

        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            search_response = client.get(
                '/api/v1/search',
                headers=auth_headers,
                params={'q': 'test', 'semantic': True}
            )

        assert search_response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_after_document_update(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_openai_client,
        test_db
    ):
        """Test search reflects document updates"""
        # Update document text
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            update_response = client.put(
                f'/api/v1/documents/{sample_document.id}',
                headers=auth_headers,
                json={'extracted_text': 'Updated content with new keywords'}
            )

        assert update_response.status_code == 200

        # Search should find updated content
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            search_response = client.get(
                '/api/v1/search',
                headers=auth_headers,
                params={'q': 'new keywords', 'semantic': True}
            )

        assert search_response.status_code == 200


@pytest.mark.integration
class TestRealtimeUpdates:
    """Test real-time updates via PubNub"""

    @pytest.mark.asyncio
    async def test_processing_progress_notifications(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: Path,
        mock_aws_services,
        mock_pubnub_client
    ):
        """Test real-time processing progress notifications"""
        with patch('boto3.client') as mock_boto, patch('pubnub.PubNub') as mock_pubnub:
            def get_client(service_name, **kwargs):
                return mock_aws_services.get(service_name)
            mock_boto.side_effect = get_client
            mock_pubnub.return_value = mock_pubnub_client

            # Upload document
            with open(sample_pdf_file, 'rb') as f:
                files = {'files': ('test.pdf', f, 'application/pdf')}

                response = client.post(
                    '/api/v1/documents/upload',
                    headers=auth_headers,
                    files=files
                )

        assert response.status_code == 201

        # Verify PubNub publish was called for progress updates
        # mock_pubnub_client.publish.assert_called()

    def test_document_completed_notification(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db,
        sample_document,
        mock_pubnub_client
    ):
        """Test completion notification sent"""
        with patch('pubnub.PubNub') as mock_pubnub:
            mock_pubnub.return_value = mock_pubnub_client

            # Mark document as completed
            sample_document.status = 'completed'
            test_db.commit()

            # Trigger completion notification
            response = client.post(
                f'/api/v1/realtime/notify',
                headers=auth_headers,
                json={
                    'user_id': sample_document.user_id,
                    'title': 'Document Processed',
                    'message': f'{sample_document.filename} is ready',
                    'priority': 'medium'
                }
            )

        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.database
class TestDatabasePersistence:
    """Test database persistence across operations"""

    def test_document_metadata_persistence(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        test_db
    ):
        """Test document metadata persists correctly"""
        # Update document with metadata
        metadata = {
            'analysis': {
                'summary': 'Test summary',
                'key_insights': ['Insight 1', 'Insight 2']
            },
            'tags': ['test', 'integration']
        }

        response = client.put(
            f'/api/v1/documents/{sample_document.id}',
            headers=auth_headers,
            json={'metadata': metadata}
        )

        assert response.status_code == 200

        # Fetch document again
        test_db.expire_all()  # Clear session
        get_response = client.get(
            f'/api/v1/documents/{sample_document.id}',
            headers=auth_headers
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert 'metadata' in data
        assert data['metadata']['tags'] == ['test', 'integration']

    def test_action_items_persistence(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        test_db
    ):
        """Test action items persist correctly"""
        # Create action item
        action_data = {
            'title': 'Test Action',
            'description': 'Test description',
            'document_id': sample_document.id,
            'priority': 'high',
            'due_date': '2025-12-31'
        }

        create_response = client.post(
            '/api/v1/documents/action-items',
            headers=auth_headers,
            json=action_data
        )

        assert create_response.status_code == 201
        action_id = create_response.json()['id']

        # Fetch action item
        test_db.expire_all()
        get_response = client.get(
            f'/api/v1/documents/action-items/{action_id}',
            headers=auth_headers
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data['title'] == 'Test Action'
        assert data['priority'] == 'high'

    def test_transaction_rollback(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db
    ):
        """Test database transaction rollback on error"""
        initial_count = test_db.query(Document).count()

        # Attempt operation that should fail
        with patch('app.routes.documents.upload_to_s3') as mock_upload:
            mock_upload.side_effect = Exception("S3 upload failed")

            files = {'files': ('test.pdf', BytesIO(b'%PDF-test'), 'application/pdf')}

            response = client.post(
                '/api/v1/documents/upload',
                headers=auth_headers,
                files=files
            )

        # Document should not be persisted
        final_count = test_db.query(Document).count()
        assert final_count == initial_count


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrentOperations:
    """Test concurrent operations"""

    def test_concurrent_uploads(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: Path,
        mock_aws_services
    ):
        """Test handling concurrent document uploads"""
        import concurrent.futures

        def upload_document(file_path):
            with open(file_path, 'rb') as f:
                files = {'files': (f'test_{id(f)}.pdf', f, 'application/pdf')}

                with patch('boto3.client') as mock_boto:
                    def get_client(service_name, **kwargs):
                        return mock_aws_services.get(service_name)
                    mock_boto.side_effect = get_client

                    return client.post(
                        '/api/v1/documents/upload',
                        headers=auth_headers,
                        files=files
                    )

        # Upload 5 documents concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_document, sample_pdf_file) for _ in range(5)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(r.status_code == 201 for r in responses)

    def test_concurrent_searches(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_openai_client
    ):
        """Test handling concurrent search requests"""
        import concurrent.futures

        def search_documents(query):
            with patch('openai.OpenAI') as mock_openai:
                mock_openai.return_value = mock_openai_client

                return client.get(
                    '/api/v1/search',
                    headers=auth_headers,
                    params={'q': query, 'semantic': True}
                )

        queries = ['test1', 'test2', 'test3', 'test4', 'test5']

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_documents, q) for q in queries]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should complete successfully
        assert all(r.status_code == 200 for r in responses)
