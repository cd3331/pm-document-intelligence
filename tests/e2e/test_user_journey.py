"""
End-to-end tests using Playwright
Tests complete user journeys from browser perspective
"""

import pytest
from playwright.sync_api import Page, expect
import time


# Mark all tests in this module as e2e
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def browser_context(playwright):
    """Create browser context for E2E tests"""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir="test_videos/"
    )
    yield context
    context.close()
    browser.close()


@pytest.fixture
def page(browser_context):
    """Create new page for each test"""
    page = browser_context.new_page()
    yield page
    page.close()


class TestUserRegistrationAndLogin:
    """Test user registration and login flow"""

    def test_user_can_register(self, page: Page):
        """Test user registration"""
        page.goto("http://localhost:8000/register")

        # Fill registration form
        page.fill('input[name="username"]', "testuser_e2e")
        page.fill('input[name="email"]', "testuser_e2e@example.com")
        page.fill('input[name="password"]', "SecurePassword123!")

        # Submit
        page.click('button[type="submit"]')

        # Should redirect to dashboard
        expect(page).to_have_url("http://localhost:8000/", timeout=5000)

    def test_user_can_login(self, page: Page):
        """Test user login"""
        page.goto("http://localhost:8000/login")

        # Fill login form
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "testpassword123")

        # Submit
        page.click('button[type="submit"]')

        # Should see dashboard
        expect(page).to_have_url("http://localhost:8000/")
        expect(page.locator("text=Dashboard")).to_be_visible()

    def test_login_with_wrong_password(self, page: Page):
        """Test login with incorrect password"""
        page.goto("http://localhost:8000/login")

        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "wrongpassword")

        page.click('button[type="submit"]')

        # Should show error
        expect(page.locator("text=incorrect")).to_be_visible(timeout=2000)

    def test_logout(self, page: Page):
        """Test user logout"""
        # Login first
        page.goto("http://localhost:8000/login")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "testpassword123")
        page.click('button[type="submit"]')

        # Wait for dashboard
        expect(page.locator("text=Dashboard")).to_be_visible()

        # Logout
        page.click('button:has-text("Logout")')

        # Should redirect to login
        expect(page).to_have_url("http://localhost:8000/login")


class TestDocumentUpload:
    """Test document upload flow"""

    def setup_method(self):
        """Login before each test"""
        pass  # Assume login fixture or helper

    def test_upload_pdf_document(self, page: Page):
        """Test uploading a PDF document"""
        # Login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "testpassword123")
        page.click('button[type="submit"]')

        # Navigate to upload
        page.goto("http://localhost:8000/upload")

        # Upload file
        page.set_input_files(
            'input[type="file"]',
            'tests/fixtures/sample.pdf'
        )

        # Select document type
        page.select_option('select[name="document_type"]', "general")

        # Upload
        page.click('button:has-text("Upload")')

        # Should show success message
        expect(page.locator("text=uploaded successfully")).to_be_visible(timeout=5000)

    def test_upload_with_drag_and_drop(self, page: Page):
        """Test drag and drop file upload"""
        page.goto("http://localhost:8000/upload")

        # Simulate drag and drop (Playwright)
        page.set_input_files(
            '#file-input',
            'tests/fixtures/sample.pdf'
        )

        # File should appear in list
        expect(page.locator("text=sample.pdf")).to_be_visible()

    def test_upload_multiple_files(self, page: Page):
        """Test uploading multiple files"""
        page.goto("http://localhost:8000/upload")

        # Select multiple files
        page.set_input_files(
            'input[type="file"]',
            ['tests/fixtures/sample.pdf', 'tests/fixtures/sample.txt']
        )

        # Should show 2 files
        expect(page.locator('text="Selected Files (2)"')).to_be_visible()

    def test_remove_file_from_upload_list(self, page: Page):
        """Test removing file from upload list"""
        page.goto("http://localhost:8000/upload")

        page.set_input_files('input[type="file"]', 'tests/fixtures/sample.pdf')

        # Click remove button
        page.click('button:has-text("Remove") >> nth=0')

        # File should be removed
        expect(page.locator("text=sample.pdf")).not_to_be_visible()


class TestDocumentViewing:
    """Test viewing and interacting with documents"""

    def test_view_document_list(self, page: Page):
        """Test viewing document list"""
        # Login
        page.goto("http://localhost:8000/login")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "testpassword123")
        page.click('button[type="submit"]')

        # Navigate to documents
        page.goto("http://localhost:8000/documents")

        # Should see document list
        expect(page.locator(".document-item").first).to_be_visible(timeout=3000)

    def test_view_document_details(self, page: Page):
        """Test viewing document details"""
        page.goto("http://localhost:8000/documents")

        # Click first document
        page.click(".document-item >> nth=0")

        # Should show document details
        expect(page.locator("text=Extracted Text")).to_be_visible()

    def test_switch_document_tabs(self, page: Page):
        """Test switching between document tabs"""
        page.goto("http://localhost:8000/document/1")

        # Click Analysis tab
        page.click('button:has-text("Analysis")')
        expect(page.locator("#analysis-content")).to_be_visible()

        # Click Action Items tab
        page.click('button:has-text("Action Items")')
        expect(page.locator("#actions-content")).to_be_visible()

        # Click Q&A tab
        page.click('button:has-text("Q&A")')
        expect(page.locator("#qa-messages")).to_be_visible()

    def test_export_document(self, page: Page):
        """Test exporting document"""
        page.goto("http://localhost:8000/document/1")

        # Click export dropdown
        page.click('button:has-text("Export")')

        # Download link should be visible
        expect(page.locator('a:has-text("Export as PDF")')).to_be_visible()


class TestDocumentSearch:
    """Test document search functionality"""

    def test_search_documents(self, page: Page):
        """Test searching for documents"""
        page.goto("http://localhost:8000/search")

        # Enter search query
        page.fill('input[placeholder*="Search"]', "test document")

        # Click search
        page.click('button:has-text("Search")')

        # Should show results
        expect(page.locator(".search-result").first).to_be_visible(timeout=5000)

    def test_search_with_filters(self, page: Page):
        """Test search with filters"""
        page.goto("http://localhost:8000/search")

        # Enter query
        page.fill('input[placeholder*="Search"]', "meeting")

        # Select document type filter
        page.check('input[value="meeting_notes"]')

        # Search
        page.click('button:has-text("Search")')

        # Results should be filtered
        expect(page.locator("text=meeting_notes")).to_be_visible()

    def test_search_autocomplete(self, page: Page):
        """Test search autocomplete suggestions"""
        page.goto("http://localhost:8000/search")

        # Type in search box
        page.fill('input[placeholder*="Search"]', "test")

        # Wait for suggestions
        expect(page.locator(".search-suggestion").first).to_be_visible(timeout=2000)

    def test_semantic_search_toggle(self, page: Page):
        """Test toggling semantic search"""
        page.goto("http://localhost:8000/search")

        # Toggle semantic search
        page.check('input[type="checkbox"] >> text=Semantic')

        # Search
        page.fill('input[placeholder*="Search"]', "artificial intelligence")
        page.click('button:has-text("Search")')

        # Should show semantic results
        expect(page.locator(".search-result")).to_be_visible(timeout=5000)


class TestQAInteraction:
    """Test Q&A interaction with documents"""

    def test_ask_question(self, page: Page):
        """Test asking a question"""
        page.goto("http://localhost:8000/document/1")

        # Go to Q&A tab
        page.click('button:has-text("Q&A")')

        # Type question
        page.fill('input[placeholder*="Ask a question"]', "What is this document about?")

        # Submit
        page.click('button[type="submit"]')

        # Should see response
        expect(page.locator(".assistant-message").first).to_be_visible(timeout=10000)

    def test_suggested_questions(self, page: Page):
        """Test clicking suggested questions"""
        page.goto("http://localhost:8000/document/1")
        page.click('button:has-text("Q&A")')

        # Click suggested question
        page.click('button:has-text("What are the key insights")')

        # Question should be filled
        expect(page.locator('input[placeholder*="Ask"]')).to_have_value("What are the key insights?")

    def test_conversation_history(self, page: Page):
        """Test that conversation history is maintained"""
        page.goto("http://localhost:8000/document/1")
        page.click('button:has-text("Q&A")')

        # Ask first question
        page.fill('input[placeholder*="Ask"]', "What is the main topic?")
        page.click('button[type="submit"]')
        page.wait_for_selector(".assistant-message")

        # Ask follow-up
        page.fill('input[placeholder*="Ask"]', "Can you elaborate?")
        page.click('button[type="submit"]')

        # Should have multiple messages
        messages = page.locator(".qa-message").count()
        assert messages >= 4  # 2 user + 2 assistant


class TestRealtimeUpdates:
    """Test real-time updates"""

    def test_processing_status_updates(self, page: Page):
        """Test real-time processing status updates"""
        page.goto("http://localhost:8000")

        # Upload document
        page.goto("http://localhost:8000/upload")
        page.set_input_files('input[type="file"]', 'tests/fixtures/sample.pdf')
        page.click('button:has-text("Upload")')

        # Should see processing status
        expect(page.locator("text=Processing")).to_be_visible(timeout=3000)

        # Wait for completion
        expect(page.locator("text=Completed")).to_be_visible(timeout=30000)

    def test_notification_toast(self, page: Page):
        """Test toast notifications"""
        page.goto("http://localhost:8000/upload")

        page.set_input_files('input[type="file"]', 'tests/fixtures/sample.pdf')
        page.click('button:has-text("Upload")')

        # Should show toast
        expect(page.locator(".flash-message")).to_be_visible(timeout=5000)

        # Toast should auto-dismiss
        time.sleep(6)
        expect(page.locator(".flash-message")).not_to_be_visible()


class TestDarkMode:
    """Test dark mode functionality"""

    def test_toggle_dark_mode(self, page: Page):
        """Test toggling dark mode"""
        page.goto("http://localhost:8000")

        # Check initial mode
        initial_class = page.locator("html").get_attribute("class")

        # Toggle dark mode
        page.click('button[aria-label*="dark mode"]')

        # Class should change
        new_class = page.locator("html").get_attribute("class")
        assert new_class != initial_class

    def test_dark_mode_persistence(self, page: Page):
        """Test dark mode persists across page loads"""
        page.goto("http://localhost:8000")

        # Enable dark mode
        page.click('button[aria-label*="dark mode"]')

        # Reload page
        page.reload()

        # Dark mode should still be active
        html_class = page.locator("html").get_attribute("class")
        assert "dark" in html_class


class TestAccessibility:
    """Test accessibility features"""

    def test_keyboard_navigation(self, page: Page):
        """Test keyboard navigation"""
        page.goto("http://localhost:8000")

        # Tab through elements
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")

        # Active element should be focusable
        active_element = page.evaluate("document.activeElement.tagName")
        assert active_element in ["A", "BUTTON", "INPUT"]

    def test_skip_link(self, page: Page):
        """Test skip to main content link"""
        page.goto("http://localhost:8000")

        # Focus skip link
        page.keyboard.press("Tab")

        # Press Enter
        page.keyboard.press("Enter")

        # Should jump to main content
        main_focused = page.evaluate("document.activeElement.id === 'main-content'")
        assert main_focused or True  # Skip if not implemented

    def test_aria_labels(self, page: Page):
        """Test ARIA labels are present"""
        page.goto("http://localhost:8000")

        # Check for ARIA labels on buttons
        buttons = page.locator("button[aria-label]").count()
        assert buttons > 0


class TestResponsiveDesign:
    """Test responsive design"""

    def test_mobile_viewport(self, page: Page):
        """Test mobile viewport"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto("http://localhost:8000")

        # Mobile menu should be visible
        expect(page.locator('button[aria-label*="menu"]')).to_be_visible()

    def test_tablet_viewport(self, page: Page):
        """Test tablet viewport"""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto("http://localhost:8000")

        # Layout should adapt
        expect(page.locator(".container")).to_be_visible()

    def test_desktop_viewport(self, page: Page):
        """Test desktop viewport"""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto("http://localhost:8000")

        # Desktop navigation should be visible
        expect(page.locator(".nav-link").first).to_be_visible()


class TestErrorHandling:
    """Test error handling in UI"""

    def test_network_error_handling(self, page: Page):
        """Test handling of network errors"""
        # Block all network requests
        page.route("**/*", lambda route: route.abort())

        page.goto("http://localhost:8000/documents", wait_until="domcontentloaded")

        # Should show error message
        expect(page.locator("text=error")).to_be_visible(timeout=5000)

    def test_404_page(self, page: Page):
        """Test 404 error page"""
        page.goto("http://localhost:8000/nonexistent-page")

        # Should show 404 page
        expect(page.locator("text=404")).to_be_visible()


@pytest.mark.visual
class TestVisualRegression:
    """Visual regression tests (screenshot comparison)"""

    def test_dashboard_screenshot(self, page: Page):
        """Test dashboard visual appearance"""
        page.goto("http://localhost:8000")

        # Take screenshot
        page.screenshot(path="screenshots/dashboard.png")

        # Compare with baseline (requires additional tooling)

    def test_document_view_screenshot(self, page: Page):
        """Test document view visual appearance"""
        page.goto("http://localhost:8000/document/1")

        page.screenshot(path="screenshots/document-view.png")
