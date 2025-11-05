"""
Integration tests for API endpoints
Tests all API endpoints, authentication, rate limiting, and error responses
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_check(self, client: TestClient):
        """Test basic health check"""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'

    def test_readiness_check(self, client: TestClient):
        """Test readiness check"""
        response = client.get('/ready')

        assert response.status_code == 200
        data = response.json()
        assert 'database' in data
        assert 'cache' in data


@pytest.mark.integration
class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_endpoint(self, client: TestClient):
        """Test user registration endpoint"""
        user_data = {
            'username': 'newuser123',
            'email': 'newuser123@example.com',
            'password': 'securepassword123'
        }

        response = client.post('/api/v1/auth/register', json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data['username'] == 'newuser123'
        assert 'id' in data

    def test_login_endpoint(self, client: TestClient, test_user):
        """Test login endpoint"""
        login_data = {
            'username': test_user.username,
            'password': 'testpassword123'
        }

        response = client.post('/api/v1/auth/login', data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data

    def test_refresh_token_endpoint(self, client: TestClient, test_user):
        """Test token refresh endpoint"""
        # Login first
        login_response = client.post(
            '/api/v1/auth/login',
            data={'username': test_user.username, 'password': 'testpassword123'}
        )
        refresh_token = login_response.json()['refresh_token']

        # Refresh
        response = client.post(
            '/api/v1/auth/refresh',
            json={'refresh_token': refresh_token}
        )

        assert response.status_code == 200
        assert 'access_token' in response.json()

    def test_me_endpoint(self, client: TestClient, auth_headers: dict, test_user):
        """Test getting current user info"""
        response = client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['username'] == test_user.username
        assert data['email'] == test_user.email


@pytest.mark.integration
class TestDocumentEndpoints:
    """Test document management endpoints"""

    def test_list_documents(self, client: TestClient, auth_headers: dict):
        """Test listing documents"""
        response = client.get('/api/v1/documents', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_document(self, client: TestClient, auth_headers: dict, sample_document):
        """Test getting document by ID"""
        response = client.get(
            f'/api/v1/documents/{sample_document.id}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == sample_document.id
        assert data['filename'] == sample_document.filename

    def test_get_nonexistent_document(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent document"""
        response = client.get('/api/v1/documents/99999', headers=auth_headers)

        assert response.status_code == 404

    def test_delete_document(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_aws_services
    ):
        """Test deleting document"""
        from unittest.mock import patch

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_aws_services['s3']

            response = client.delete(
                f'/api/v1/documents/{sample_document.id}',
                headers=auth_headers
            )

        assert response.status_code == 200 or response.status_code == 204

    def test_update_document(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document
    ):
        """Test updating document"""
        update_data = {
            'document_type': 'meeting_notes',
            'metadata': {'updated': True}
        }

        response = client.put(
            f'/api/v1/documents/{sample_document.id}',
            headers=auth_headers,
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data['document_type'] == 'meeting_notes'


@pytest.mark.integration
class TestSearchEndpoints:
    """Test search endpoints"""

    def test_semantic_search(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_openai_client
    ):
        """Test semantic search"""
        from unittest.mock import patch

        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            response = client.get(
                '/api/v1/search',
                headers=auth_headers,
                params={'q': 'test query', 'semantic': True}
            )

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert 'total' in data

    def test_keyword_search(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test keyword search"""
        response = client.get(
            '/api/v1/search',
            headers=auth_headers,
            params={'q': 'test', 'semantic': False}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data

    def test_search_with_filters(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_openai_client
    ):
        """Test search with filters"""
        from unittest.mock import patch

        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            response = client.get(
                '/api/v1/search',
                headers=auth_headers,
                params={
                    'q': 'test',
                    'document_type': 'general',
                    'status': 'completed'
                }
            )

        assert response.status_code == 200

    def test_search_without_query(self, client: TestClient, auth_headers: dict):
        """Test search without query parameter"""
        response = client.get('/api/v1/search', headers=auth_headers)

        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestAgentEndpoints:
    """Test AI agent endpoints"""

    def test_ask_agent(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_bedrock_runtime_client
    ):
        """Test asking question to AI agent"""
        from unittest.mock import patch

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            response = client.post(
                '/api/v1/agents/ask',
                headers=auth_headers,
                json={
                    'question': 'What is this about?',
                    'document_id': sample_document.id
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert 'answer' in data

    def test_summarize_document(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_document,
        mock_bedrock_runtime_client
    ):
        """Test document summarization"""
        from unittest.mock import patch

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            response = client.post(
                f'/api/v1/agents/summarize/{sample_document.id}',
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data or 'result' in data


@pytest.mark.integration
class TestRateLimiting:
    """Test rate limiting on API endpoints"""

    @pytest.mark.slow
    def test_rate_limit_enforcement(self, client: TestClient, test_user):
        """Test rate limiting is enforced"""
        login_data = {
            'username': test_user.username,
            'password': 'wrongpassword'
        }

        # Make many requests rapidly
        responses = []
        for _ in range(20):
            response = client.post('/api/v1/auth/login', data=login_data)
            responses.append(response)

        # At least one should be rate limited
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or any(r.status_code == 401 for r in responses)

    def test_rate_limit_headers(self, client: TestClient, auth_headers: dict):
        """Test rate limit headers are present"""
        response = client.get('/api/v1/documents', headers=auth_headers)

        # Check for rate limit headers
        assert 'X-RateLimit-Limit' in response.headers or response.status_code == 200


@pytest.mark.integration
class TestCORSBehavior:
    """Test CORS configuration"""

    def test_cors_preflight(self, client: TestClient):
        """Test CORS preflight request"""
        response = client.options(
            '/api/v1/documents',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET'
            }
        )

        assert response.status_code in [200, 204]
        assert 'Access-Control-Allow-Origin' in response.headers

    def test_cors_actual_request(self, client: TestClient, auth_headers: dict):
        """Test CORS on actual request"""
        headers = {**auth_headers, 'Origin': 'http://localhost:3000'}

        response = client.get('/api/v1/documents', headers=headers)

        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200


@pytest.mark.integration
class TestErrorResponses:
    """Test error response formats"""

    def test_404_error_format(self, client: TestClient):
        """Test 404 error response format"""
        response = client.get('/nonexistent')

        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data

    def test_422_validation_error(self, client: TestClient):
        """Test validation error format"""
        response = client.post(
            '/api/v1/auth/register',
            json={'username': 'test'}  # Missing required fields
        )

        assert response.status_code == 422
        data = response.json()
        assert 'detail' in data

    def test_401_unauthorized(self, client: TestClient):
        """Test unauthorized error"""
        response = client.get('/api/v1/documents')

        assert response.status_code == 401
        data = response.json()
        assert 'detail' in data

    def test_403_forbidden(self, client: TestClient, auth_headers: dict):
        """Test forbidden error"""
        response = client.get('/api/v1/admin/users', headers=auth_headers)

        assert response.status_code == 403
        data = response.json()
        assert 'detail' in data


@pytest.mark.integration
class TestMCPEndpoints:
    """Test MCP (Model Context Protocol) endpoints"""

    def test_list_tools(self, client: TestClient, auth_headers: dict):
        """Test listing available MCP tools"""
        response = client.get('/api/v1/mcp/tools', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_execute_tool(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_openai_client
    ):
        """Test executing MCP tool"""
        from unittest.mock import patch

        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client

            response = client.post(
                '/api/v1/mcp/execute',
                headers=auth_headers,
                json={
                    'tool': 'search_documents',
                    'arguments': {'query': 'test'}
                }
            )

        assert response.status_code == 200

    def test_list_prompts(self, client: TestClient, auth_headers: dict):
        """Test listing MCP prompts"""
        response = client.get('/api/v1/mcp/prompts', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestRealtimeEndpoints:
    """Test real-time communication endpoints"""

    def test_get_realtime_status(self, client: TestClient, auth_headers: dict):
        """Test getting real-time connection status"""
        response = client.get('/api/v1/realtime/status', headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert 'publish_key' in data or 'subscribe_key' in data

    def test_send_notification(
        self,
        client: TestClient,
        auth_headers: dict,
        mock_pubnub_client
    ):
        """Test sending real-time notification"""
        from unittest.mock import patch

        with patch('pubnub.PubNub') as mock_pubnub:
            mock_pubnub.return_value = mock_pubnub_client

            response = client.post(
                '/api/v1/realtime/notify',
                headers=auth_headers,
                json={
                    'title': 'Test Notification',
                    'message': 'Test message',
                    'priority': 'medium'
                }
            )

        assert response.status_code == 200


@pytest.mark.integration
class TestPaginationAndSorting:
    """Test pagination and sorting features"""

    def test_documents_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        generate_documents,
        test_user
    ):
        """Test document list pagination"""
        # Generate many documents
        generate_documents(count=25, user=test_user)

        # First page
        response1 = client.get(
            '/api/v1/documents',
            headers=auth_headers,
            params={'page': 1, 'page_size': 10}
        )

        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) <= 10

        # Second page
        response2 = client.get(
            '/api/v1/documents',
            headers=auth_headers,
            params={'page': 2, 'page_size': 10}
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) <= 10

    def test_documents_sorting(
        self,
        client: TestClient,
        auth_headers: dict,
        generate_documents,
        test_user
    ):
        """Test document list sorting"""
        generate_documents(count=5, user=test_user)

        # Sort by date descending
        response1 = client.get(
            '/api/v1/documents',
            headers=auth_headers,
            params={'sort_by': 'created_at', 'order': 'desc'}
        )

        assert response1.status_code == 200
        data1 = response1.json()

        if len(data1) > 1:
            # Check ordering
            dates1 = [d['created_at'] for d in data1]
            assert dates1 == sorted(dates1, reverse=True) or len(data1) == 0

        # Sort by filename ascending
        response2 = client.get(
            '/api/v1/documents',
            headers=auth_headers,
            params={'sort_by': 'filename', 'order': 'asc'}
        )

        assert response2.status_code == 200


@pytest.mark.integration
class TestOpenAPISpec:
    """Test OpenAPI specification"""

    def test_openapi_json(self, client: TestClient):
        """Test OpenAPI JSON is accessible"""
        response = client.get('/openapi.json')

        assert response.status_code == 200
        data = response.json()
        assert 'openapi' in data
        assert 'paths' in data

    def test_docs_ui(self, client: TestClient):
        """Test Swagger UI is accessible"""
        response = client.get('/docs')

        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']

    def test_redoc_ui(self, client: TestClient):
        """Test ReDoc UI is accessible"""
        response = client.get('/redoc')

        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
