"""
htmx API routes for HTML fragments
These routes return HTML fragments for dynamic page updates via htmx
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Document, ActionItem
from app.services.vector_search import VectorSearch
from app.agents.orchestrator import get_orchestrator

router = APIRouter(tags=["htmx"])

vector_search = VectorSearch()
orchestrator = get_orchestrator()


@router.get("/api/stats", response_class=HTMLResponse)
async def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns statistics cards HTML
    Used by dashboard to show document counts and metrics
    """
    # Get document counts
    total_documents = (
        db.query(func.count(Document.id)).filter(Document.user_id == current_user.id).scalar() or 0
    )

    completed_documents = (
        db.query(func.count(Document.id))
        .filter(Document.user_id == current_user.id, Document.status == "completed")
        .scalar()
        or 0
    )

    processing_documents = (
        db.query(func.count(Document.id))
        .filter(Document.user_id == current_user.id, Document.status == "processing")
        .scalar()
        or 0
    )

    # Get action items count
    pending_actions = (
        db.query(func.count(ActionItem.id))
        .filter(ActionItem.user_id == current_user.id, ActionItem.status == "pending")
        .scalar()
        or 0
    )

    html = f"""
    <div class="card">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-600 dark:text-gray-400">Total Documents</p>
                <p class="text-3xl font-bold text-gray-900 dark:text-white">{total_documents}</p>
            </div>
            <div class="w-12 h-12 bg-joy-teal/10 rounded-lg flex items-center justify-center">
                <i class="fas fa-file-alt text-2xl text-joy-teal"></i>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-600 dark:text-gray-400">Completed</p>
                <p class="text-3xl font-bold text-gray-900 dark:text-white">{completed_documents}</p>
            </div>
            <div class="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                <i class="fas fa-check-circle text-2xl text-green-600 dark:text-green-400"></i>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-600 dark:text-gray-400">Processing</p>
                <p class="text-3xl font-bold text-gray-900 dark:text-white">{processing_documents}</p>
            </div>
            <div class="w-12 h-12 bg-yellow-100 dark:bg-yellow-900 rounded-lg flex items-center justify-center">
                <i class="fas fa-spinner text-2xl text-yellow-600 dark:text-yellow-400"></i>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-600 dark:text-gray-400">Pending Actions</p>
                <p class="text-3xl font-bold text-gray-900 dark:text-white">{pending_actions}</p>
            </div>
            <div class="w-12 h-12 bg-warm-coral/10 rounded-lg flex items-center justify-center">
                <i class="fas fa-tasks text-2xl text-warm-coral"></i>
            </div>
        </div>
    </div>
    """

    return HTMLResponse(content=html)


@router.get("/api/documents/list", response_class=HTMLResponse)
async def get_documents_list(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns document list HTML
    Used by dashboard and documents page
    """
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(desc(Document.created_at))
        .limit(limit)
        .all()
    )

    if not documents:
        return HTMLResponse(
            content="""
            <div class="text-center py-8">
                <i class="fas fa-folder-open text-4xl text-gray-300 dark:text-gray-600 mb-4"></i>
                <p class="text-gray-600 dark:text-gray-400">No documents yet</p>
                <a href="/upload" class="btn-primary mt-4">
                    <i class="fas fa-upload mr-2"></i> Upload Your First Document
                </a>
            </div>
        """
        )

    html_parts = []
    for doc in documents:
        # Status badge classes
        status_class = ""
        if doc.status == "completed":
            status_class = "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
        elif doc.status == "processing":
            status_class = "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
        elif doc.status == "failed":
            status_class = "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"

        # File icon
        icon_class = "fa-file-alt"
        if doc.filename.endswith(".pdf"):
            icon_class = "fa-file-pdf text-red-500"
        elif doc.filename.endswith((".docx", ".doc")):
            icon_class = "fa-file-word text-blue-500"
        elif doc.filename.endswith(".txt"):
            icon_class = "fa-file-alt text-gray-500"
        elif doc.filename.endswith((".png", ".jpg", ".jpeg")):
            icon_class = "fa-file-image text-green-500"

        created_at = (
            doc.created_at.strftime("%b %d, %Y at %I:%M %p") if doc.created_at else "Unknown"
        )

        html_parts.append(
            f"""
        <div class="flex items-center space-x-4 p-4 border dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
             onclick="window.location.href='/document/{doc.id}'">
            <div class="w-12 h-12 bg-joy-teal/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <i class="fas {icon_class} text-2xl"></i>
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="font-semibold text-gray-900 dark:text-white truncate">{doc.filename}</h3>
                <div class="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                    <span><i class="fas fa-clock mr-1"></i> {created_at}</span>
                    <span><i class="fas fa-file mr-1"></i> {doc.document_type}</span>
                </div>
            </div>
            <span class="px-2 py-1 rounded text-xs font-medium {status_class}">
                {doc.status}
            </span>
        </div>
        """
        )

    html = "\n".join(html_parts)
    return HTMLResponse(content=html)


@router.get("/api/documents/recent", response_class=HTMLResponse)
async def get_recent_documents(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns recent documents HTML
    Same as documents/list but can have different styling
    """
    return await get_documents_list(limit=limit, current_user=current_user, db=db)


@router.get("/api/document/{document_id}/analysis", response_class=HTMLResponse)
async def get_document_analysis(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns document analysis tab HTML
    Lazy-loaded when user clicks Analysis tab
    """
    # Get document
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        return HTMLResponse(
            content="""
            <div class="card">
                <p class="text-red-600 dark:text-red-400">Document not found</p>
            </div>
        """
        )

    if document.status != "completed":
        return HTMLResponse(
            content="""
            <div class="card">
                <div class="text-center py-8">
                    <i class="fas fa-spinner fa-spin text-4xl text-joy-teal mb-4"></i>
                    <p class="text-gray-600 dark:text-gray-400">Analysis in progress...</p>
                </div>
            </div>
        """
        )

    # Parse analysis from metadata
    analysis = document.metadata.get("analysis", {}) if document.metadata else {}

    html = f"""
    <div class="space-y-6">
        <!-- Summary -->
        <div class="card">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Summary</h3>
            <p class="text-gray-700 dark:text-gray-300">{analysis.get('summary', 'No summary available')}</p>
        </div>

        <!-- Key Insights -->
        <div class="card">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Key Insights</h3>
            <ul class="space-y-2">
    """

    insights = analysis.get("key_insights", [])
    if insights:
        for insight in insights:
            html += f'<li class="flex items-start space-x-2"><i class="fas fa-lightbulb text-joy-teal mt-1"></i><span class="text-gray-700 dark:text-gray-300">{insight}</span></li>'
    else:
        html += '<li class="text-gray-600 dark:text-gray-400">No key insights available</li>'

    html += """
            </ul>
        </div>

        <!-- Sentiment -->
        <div class="card">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Sentiment Analysis</h3>
    """

    sentiment = analysis.get("sentiment", "neutral")
    sentiment_color = {
        "positive": "text-green-600 dark:text-green-400",
        "neutral": "text-gray-600 dark:text-gray-400",
        "negative": "text-red-600 dark:text-red-400",
    }.get(sentiment, "text-gray-600")

    html += f'<p class="{sentiment_color} font-medium capitalize">{sentiment}</p>'

    html += """
        </div>
    </div>
    """

    return HTMLResponse(content=html)


@router.get("/api/document/{document_id}/actions", response_class=HTMLResponse)
async def get_document_actions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns document action items tab HTML
    Lazy-loaded when user clicks Action Items tab
    """
    # Get action items for this document
    action_items = (
        db.query(ActionItem)
        .filter(ActionItem.document_id == document_id, ActionItem.user_id == current_user.id)
        .order_by(ActionItem.priority.desc(), ActionItem.created_at)
        .all()
    )

    if not action_items:
        return HTMLResponse(
            content="""
            <div class="card">
                <div class="text-center py-8">
                    <i class="fas fa-tasks text-4xl text-gray-300 dark:text-gray-600 mb-4"></i>
                    <p class="text-gray-600 dark:text-gray-400">No action items found</p>
                </div>
            </div>
        """
        )

    html = '<div class="card"><div class="space-y-4">'

    for item in action_items:
        # Status checkbox
        checked = "checked" if item.status == "completed" else ""

        # Priority badge
        priority_class = {
            "high": "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
            "medium": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
            "low": "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
        }.get(item.priority, "bg-gray-100")

        due_date = item.due_date.strftime("%b %d, %Y") if item.due_date else "No due date"

        html += f"""
        <div class="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <input type="checkbox" {checked}
                   class="mt-1 rounded border-gray-300 text-joy-teal focus:ring-joy-teal"
                   onchange="updateActionStatus({item.id}, this.checked)">
            <div class="flex-1">
                <div class="flex items-start justify-between">
                    <p class="font-medium text-gray-900 dark:text-white">{item.title}</p>
                    <span class="ml-2 px-2 py-1 rounded text-xs font-medium {priority_class}">
                        {item.priority}
                    </span>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{item.description or ''}</p>
                <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-500">
                    <span><i class="fas fa-calendar mr-1"></i> {due_date}</span>
                    {f'<span><i class="fas fa-user mr-1"></i> {item.assignee}</span>' if item.assignee else ''}
                </div>
            </div>
        </div>
        """

    html += "</div></div>"

    return HTMLResponse(content=html)


@router.get("/api/processing/status", response_class=HTMLResponse)
async def get_processing_status(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Returns processing status HTML
    Shows documents currently being processed
    """
    processing_docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.status == "processing")
        .all()
    )

    if not processing_docs:
        return HTMLResponse(
            content="""
            <p class="text-sm text-gray-600 dark:text-gray-400 text-center py-4">
                No documents processing
            </p>
        """
        )

    html_parts = []
    for doc in processing_docs:
        # Get progress from metadata
        progress = doc.metadata.get("progress", 0) if doc.metadata else 0
        current_step = (
            doc.metadata.get("current_step", "Processing") if doc.metadata else "Processing"
        )

        html_parts.append(
            f"""
        <div class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg" data-document-id="{doc.id}">
            <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{doc.filename}</p>
                <span class="text-xs text-gray-600 dark:text-gray-400">{progress}%</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {progress}%"></div>
            </div>
            <p class="text-xs text-gray-600 dark:text-gray-400 mt-1 progress-text">{current_step}</p>
        </div>
        """
        )

    html = "\n".join(html_parts)
    return HTMLResponse(content=html)


@router.get("/api/search/suggestions", response_class=HTMLResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns search suggestions HTML
    Used for autocomplete in search bar
    """
    # Search for matching documents
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.filename.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )

    if not documents:
        return HTMLResponse(content="")

    suggestions = []
    for doc in documents:
        suggestions.append(
            {
                "id": doc.id,
                "text": doc.filename,
                "source": f"{doc.document_type} - {doc.created_at.strftime('%b %d, %Y')}",
            }
        )

    # Return as JSON for Alpine.js to handle
    # Note: This endpoint returns JSON, not HTML
    from fastapi.responses import JSONResponse

    return JSONResponse(content={"suggestions": suggestions})


@router.get("/api/search", response_class=HTMLResponse)
async def search_documents(
    q: str = Query(..., min_length=1),
    semantic: bool = Query(True),
    sort: str = Query("relevance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    types: Optional[str] = Query(None),
    statuses: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search documents and return results
    Returns JSON for Alpine.js to handle
    """
    results = []
    total = 0

    try:
        if semantic:
            # Use vector search
            search_results = await vector_search.search(
                query=q,
                user_id=current_user.id,
                limit=page_size,
                offset=(page - 1) * page_size,
            )
            results = search_results.get("results", [])
            total = search_results.get("total", 0)
        else:
            # Use keyword search
            query = db.query(Document).filter(Document.user_id == current_user.id)

            # Apply filters
            if types:
                type_list = types.split(",")
                query = query.filter(Document.document_type.in_(type_list))

            if statuses:
                status_list = statuses.split(",")
                query = query.filter(Document.status.in_(status_list))

            if date_from:
                query = query.filter(Document.created_at >= datetime.fromisoformat(date_from))

            if date_to:
                query = query.filter(Document.created_at <= datetime.fromisoformat(date_to))

            # Apply search
            query = query.filter(
                Document.filename.ilike(f"%{q}%") | Document.extracted_text.ilike(f"%{q}%")
            )

            # Apply sorting
            if sort == "date_desc":
                query = query.order_by(desc(Document.created_at))
            elif sort == "date_asc":
                query = query.order_by(Document.created_at)
            elif sort == "name_asc":
                query = query.order_by(Document.filename)
            elif sort == "name_desc":
                query = query.order_by(desc(Document.filename))

            total = query.count()
            documents = query.offset((page - 1) * page_size).limit(page_size).all()

            for doc in documents:
                results.append(
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "document_type": doc.document_type,
                        "status": doc.status,
                        "created_at": doc.created_at.strftime("%b %d, %Y"),
                        "excerpt": (doc.extracted_text[:200] + "..." if doc.extracted_text else ""),
                        "tags": doc.metadata.get("tags", []) if doc.metadata else [],
                    }
                )

    except Exception as e:
        print(f"Search error: {e}")

    # Return JSON for Alpine.js
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
