"""
Load and performance tests using Locust
Tests system performance under concurrent load
"""

from locust import HttpUser, task, between, events
import random
import json
from io import BytesIO


# Test data
SAMPLE_USERS = [
    {"username": f"loadtest_user_{i}", "password": "testpassword123"}
    for i in range(10)
]

SAMPLE_QUERIES = [
    "project management",
    "meeting notes",
    "action items",
    "financial report",
    "technical documentation"
]


class DocumentIntelligenceUser(HttpUser):
    """
    Simulates a user interacting with the PM Document Intelligence system
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://localhost:8000"

    def on_start(self):
        """Login when user starts"""
        self.login()

    def login(self):
        """Authenticate and get token"""
        # Try to login with existing user
        user_creds = random.choice(SAMPLE_USERS)

        # First try to register (may fail if user exists)
        self.client.post(
            "/api/v1/auth/register",
            json={
                "username": user_creds["username"],
                "email": f"{user_creds['username']}@example.com",
                "password": user_creds["password"]
            },
            name="Register User"
        )

        # Login
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": user_creds["username"],
                "password": user_creds["password"]
            },
            name="Login"
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(5)
    def list_documents(self):
        """List documents (high frequency)"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/documents",
            headers=self.headers,
            name="List Documents"
        )

    @task(3)
    def search_documents(self):
        """Search documents (medium frequency)"""
        if not self.token:
            return

        query = random.choice(SAMPLE_QUERIES)

        self.client.get(
            "/api/v1/search",
            params={
                "q": query,
                "semantic": random.choice([True, False])
            },
            headers=self.headers,
            name="Search Documents"
        )

    @task(2)
    def view_document(self):
        """View document details (medium frequency)"""
        if not self.token:
            return

        # Get list of documents first
        response = self.client.get(
            "/api/v1/documents",
            headers=self.headers
        )

        if response.status_code == 200 and response.json():
            docs = response.json()
            if docs:
                doc_id = docs[0].get("id")
                self.client.get(
                    f"/api/v1/documents/{doc_id}",
                    headers=self.headers,
                    name="View Document"
                )

    @task(1)
    def upload_document(self):
        """Upload document (low frequency)"""
        if not self.token:
            return

        # Create mock PDF content
        pdf_content = b"%PDF-1.4\nTest PDF content for load testing"

        files = {
            "files": ("loadtest.pdf", BytesIO(pdf_content), "application/pdf")
        }

        data = {
            "document_type": "general",
            "auto_analyze": "false"  # Don't analyze to save resources
        }

        self.client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=self.headers,
            name="Upload Document"
        )

    @task(2)
    def ask_question(self):
        """Ask AI question (medium frequency)"""
        if not self.token:
            return

        # Get a document first
        response = self.client.get(
            "/api/v1/documents",
            headers=self.headers
        )

        if response.status_code == 200 and response.json():
            docs = response.json()
            if docs:
                doc_id = docs[0].get("id")

                self.client.post(
                    "/api/v1/agents/ask",
                    json={
                        "question": "What is this document about?",
                        "document_id": doc_id
                    },
                    headers=self.headers,
                    name="Ask Question"
                )

    @task(1)
    def get_stats(self):
        """Get dashboard stats (low frequency)"""
        if not self.token:
            return

        self.client.get(
            "/api/stats",
            headers=self.headers,
            name="Get Stats"
        )


class AdminUser(HttpUser):
    """
    Simulates admin user performing administrative tasks
    """

    wait_time = between(2, 5)
    host = "http://localhost:8000"

    def on_start(self):
        """Login as admin"""
        # Login as admin
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "adminuser",
                "password": "adminpassword123"
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(5)
    def list_all_users(self):
        """List all users"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/admin/users",
            headers=self.headers,
            name="Admin: List Users"
        )

    @task(3)
    def view_system_metrics(self):
        """View system metrics"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/admin/metrics",
            headers=self.headers,
            name="Admin: View Metrics"
        )

    @task(2)
    def view_processing_queue(self):
        """View processing queue"""
        if not self.token:
            return

        self.client.get(
            "/api/v1/admin/processing-queue",
            headers=self.headers,
            name="Admin: Processing Queue"
        )


class ApiOnlyUser(HttpUser):
    """
    Simulates API-only client (no browser)
    """

    wait_time = between(0.5, 1.5)  # Faster than regular users
    host = "http://localhost:8000"

    def on_start(self):
        """Setup API client"""
        # Use API key instead of JWT
        self.headers = {
            "X-API-Key": "test-api-key-for-load-testing"
        }

    @task(10)
    def api_search(self):
        """API search requests"""
        query = random.choice(SAMPLE_QUERIES)

        self.client.get(
            "/api/v1/search",
            params={"q": query},
            headers=self.headers,
            name="API: Search"
        )

    @task(5)
    def api_list_documents(self):
        """API list documents"""
        self.client.get(
            "/api/v1/documents",
            headers=self.headers,
            name="API: List Documents"
        )

    @task(2)
    def api_health_check(self):
        """API health check"""
        self.client.get(
            "/health",
            name="API: Health Check"
        )


# Event handlers for custom metrics

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("=" * 60)
    print("Load Test Starting")
    print(f"Host: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("\n" + "=" * 60)
    print("Load Test Complete")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Requests per second: {environment.stats.total.total_rps:.2f}")
    print("=" * 60)

    # Generate report
    stats = environment.stats

    # Identify bottlenecks (requests with high response times)
    print("\nPerformance Bottlenecks:")
    print("-" * 60)
    bottlenecks = []
    for stat in stats.entries.values():
        if stat.avg_response_time > 1000:  # Over 1 second
            bottlenecks.append((stat.name, stat.avg_response_time))

    if bottlenecks:
        for name, avg_time in sorted(bottlenecks, key=lambda x: x[1], reverse=True):
            print(f"  - {name}: {avg_time:.2f}ms")
    else:
        print("  No significant bottlenecks detected")

    # Identify failures
    print("\nRequest Failures:")
    print("-" * 60)
    failures = []
    for stat in stats.entries.values():
        if stat.num_failures > 0:
            failures.append((stat.name, stat.num_failures, stat.num_requests))

    if failures:
        for name, num_failures, total in failures:
            failure_rate = (num_failures / total) * 100
            print(f"  - {name}: {num_failures}/{total} ({failure_rate:.2f}%)")
    else:
        print("  No failures")

    print("=" * 60)


# Custom load test scenarios

class SpikeLoadTest(HttpUser):
    """
    Simulates sudden spike in traffic
    Useful for testing autoscaling and rate limiting
    """

    wait_time = between(0.1, 0.5)  # Very short wait time
    host = "http://localhost:8000"

    def on_start(self):
        """Quick login"""
        user_creds = random.choice(SAMPLE_USERS)
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": user_creds["username"],
                "password": user_creds["password"]
            }
        )

        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task
    def rapid_fire_requests(self):
        """Make rapid requests"""
        if not self.token:
            return

        endpoints = [
            "/api/v1/documents",
            "/api/v1/search?q=test",
            "/api/stats"
        ]

        endpoint = random.choice(endpoints)
        self.client.get(endpoint, headers=self.headers, name="Spike: Rapid Request")


class SteadyStateTest(HttpUser):
    """
    Simulates steady-state load over extended period
    Useful for identifying memory leaks and resource exhaustion
    """

    wait_time = between(5, 10)  # Longer wait time
    host = "http://localhost:8000"

    def on_start(self):
        """Login"""
        user_creds = random.choice(SAMPLE_USERS)
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": user_creds["username"],
                "password": user_creds["password"]
            }
        )

        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def normal_operation(self):
        """Normal read operations"""
        if not self.token:
            return

        self.client.get("/api/v1/documents", headers=self.headers)

    @task(1)
    def periodic_write(self):
        """Occasional write operations"""
        if not self.token:
            return

        # Simulate updating document
        docs_response = self.client.get("/api/v1/documents", headers=self.headers)

        if docs_response.status_code == 200 and docs_response.json():
            docs = docs_response.json()
            if docs:
                doc_id = docs[0].get("id")
                self.client.put(
                    f"/api/v1/documents/{doc_id}",
                    json={"metadata": {"load_test": True}},
                    headers=self.headers
                )


# Command to run:
# locust -f tests/load/test_performance.py --host=http://localhost:8000
#
# For web UI:
# locust -f tests/load/test_performance.py --host=http://localhost:8000 --web-port=8089
#
# For headless mode:
# locust -f tests/load/test_performance.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 5m
#   -u: number of users
#   -r: spawn rate (users per second)
#   -t: run time
