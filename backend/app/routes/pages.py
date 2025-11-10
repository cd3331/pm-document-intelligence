"""
Page routes for rendering HTML templates
These routes serve the main application pages using Jinja2 templates
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import execute_select
from app.models.user import UserInDB
from app.utils.auth_helpers import get_current_user, get_current_user_optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize router
router = APIRouter(tags=["pages"])

# Set up templates directory
templates_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "templates"
)
templates = Jinja2Templates(directory=templates_dir)


# Add custom filters and functions to Jinja2
def format_datetime(value):
    """Format datetime for display"""
    if not value:
        return ""
    if isinstance(value, str):
        from datetime import datetime

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y at %I:%M %p")
        except:
            return value
    return value.strftime("%b %d, %Y at %I:%M %p")


def format_date(value):
    """Format date for display"""
    if not value:
        return ""
    if isinstance(value, str):
        from datetime import datetime

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y")
        except:
            return value
    return value.strftime("%b %d, %Y")


templates.env.filters["datetime"] = format_datetime
templates.env.filters["date"] = format_date


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    current_user: UserInDB | None = Depends(get_current_user_optional),
):
    """
    Dashboard / Home page
    Displays overview of documents, statistics, and quick actions
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Upload page
    Allows users to upload new documents
    """
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/document/{document_id}", response_class=HTMLResponse)
async def document_detail(
    request: Request,
    document_id: str,  # UUID as string
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Document detail page
    Displays document content, analysis, action items, and Q&A
    """
    try:
        # Get document using execute_select helper
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document = documents[0]

        return templates.TemplateResponse(
            "document.html",
            {
                "request": request,
                "user": current_user,
                "document": document,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading document page: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load document",
        )


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Search page
    Allows users to search documents with filters
    """
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    All documents page
    Lists all user documents with filtering and sorting
    """
    try:
        # Get all user documents using execute_select helper
        documents = await execute_select(
            "documents",
            match={"user_id": current_user.id},
            order="created_at.desc",
        )

        return templates.TemplateResponse(
            "documents.html",
            {
                "request": request,
                "user": current_user,
                "documents": documents,
            },
        )

    except Exception as e:
        logger.error(f"Error loading documents page: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load documents",
        )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Settings page
    User preferences and account settings
    """
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    User profile page
    View and edit user profile information
    """
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str | None = None):
    """
    Login page
    User authentication
    """
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "next": next,
        },
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Registration page
    New user signup
    """
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
        },
    )


@router.get("/docs", response_class=HTMLResponse)
async def documentation_page(request: Request):
    """
    Documentation page
    User guide and API documentation
    """
    return templates.TemplateResponse(
        "docs.html",
        {
            "request": request,
        },
    )


@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    """
    Help page
    FAQs and support information
    """
    return templates.TemplateResponse(
        "help.html",
        {
            "request": request,
        },
    )


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """
    About page
    Information about the application
    """
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
        },
    )


# Error pages
@router.get("/404", response_class=HTMLResponse)
async def not_found_page(request: Request):
    """404 Not Found page"""
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
        },
        status_code=status.HTTP_404_NOT_FOUND,
    )


@router.get("/500", response_class=HTMLResponse)
async def server_error_page(request: Request):
    """500 Internal Server Error page"""
    return templates.TemplateResponse(
        "500.html",
        {
            "request": request,
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
