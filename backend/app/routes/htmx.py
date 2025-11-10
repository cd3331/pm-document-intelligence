"""
htmx API routes for HTML fragments
These routes return HTML fragments for dynamic page updates via htmx
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import execute_select
from app.models.user import UserInDB
from app.utils.auth_helpers import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["htmx"])


@router.get("/api/stats", response_class=HTMLResponse)
async def get_stats(current_user: UserInDB = Depends(get_current_user)):
    """
    Returns statistics cards HTML
    Used by dashboard to show document counts and metrics
    """
    try:
        # Get all documents for user
        documents = await execute_select(
            "documents",
            match={"user_id": current_user.id},
        )

        total_documents = len(documents)
        completed_documents = len([d for d in documents if d.get("status") == "processed"])
        processing_documents = len([d for d in documents if d.get("status") == "processing"])

        # Note: Action items table may not exist, so we'll show 0 for now
        pending_actions = 0

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

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return HTMLResponse(
            content='<div class="text-red-600">Failed to load statistics</div>',
            status_code=500,
        )


@router.get("/api/documents/list", response_class=HTMLResponse)
async def get_documents_list(
    limit: int = Query(10, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns document list HTML
    Used by dashboard and documents page
    """
    try:
        documents = await execute_select(
            "documents",
            match={"user_id": current_user.id},
            order="created_at.desc",
            limit=limit,
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
            status = doc.get("status", "uploaded")
            status_class = ""
            if status == "processed":
                status_class = "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
            elif status == "processing":
                status_class = "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
            elif status == "failed":
                status_class = "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
            else:
                status_class = "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"

            # File icon
            filename = doc.get("filename", "")
            icon_class = "fa-file-alt"
            if filename.endswith(".pdf"):
                icon_class = "fa-file-pdf text-red-500"
            elif filename.endswith((".docx", ".doc")):
                icon_class = "fa-file-word text-blue-500"
            elif filename.endswith(".txt"):
                icon_class = "fa-file-alt text-gray-500"
            elif filename.endswith((".png", ".jpg", ".jpeg")):
                icon_class = "fa-file-image text-green-500"

            created_at_str = "Unknown"
            if doc.get("created_at"):
                if isinstance(doc["created_at"], str):
                    try:
                        created_dt = datetime.fromisoformat(
                            doc["created_at"].replace("Z", "+00:00")
                        )
                        created_at_str = created_dt.strftime("%b %d, %Y at %I:%M %p")
                    except:
                        created_at_str = doc["created_at"]
                else:
                    created_at_str = doc["created_at"].strftime("%b %d, %Y at %I:%M %p")

            doc_type = doc.get("file_type", "unknown")

            html_parts.append(
                f"""
        <div class="flex items-center space-x-4 p-4 border dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
             onclick="window.location.href='/document/{doc["id"]}'">
            <div class="w-12 h-12 bg-joy-teal/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <i class="fas {icon_class} text-2xl"></i>
            </div>
            <div class="flex-1 min-w-0">
                <h3 class="font-semibold text-gray-900 dark:text-white truncate">{filename}</h3>
                <div class="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                    <span><i class="fas fa-clock mr-1"></i> {created_at_str}</span>
                    <span><i class="fas fa-file mr-1"></i> {doc_type}</span>
                </div>
            </div>
            <span class="px-2 py-1 rounded text-xs font-medium {status_class}">
                {status}
            </span>
        </div>
        """
            )

        html = "\n".join(html_parts)
        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Failed to get documents list: {e}", exc_info=True)
        return HTMLResponse(
            content='<div class="text-red-600">Failed to load documents</div>',
            status_code=500,
        )


@router.get("/api/documents/recent", response_class=HTMLResponse)
async def get_recent_documents(
    limit: int = Query(10, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns recent documents HTML
    Same as documents/list but can have different styling
    """
    return await get_documents_list(limit=limit, current_user=current_user)


@router.get("/api/document/{document_id}/analysis", response_class=HTMLResponse)
async def get_document_analysis(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns document analysis tab HTML
    Lazy-loaded when user clicks Analysis tab
    """
    try:
        # Get document
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            return HTMLResponse(
                content="""
            <div class="card">
                <p class="text-red-600 dark:text-red-400">Document not found</p>
            </div>
        """
            )

        document = documents[0]

        if document.get("status") != "processed":
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

        # Get analysis data
        summary = document.get("summary", "No summary available")
        key_phrases = document.get("key_phrases", [])
        entities = document.get("entities", [])

        html = f"""
    <div class="space-y-6">
        <!-- Summary -->
        <div class="card">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Summary</h3>
            <p class="text-gray-700 dark:text-gray-300">{summary}</p>
        </div>

        <!-- Key Phrases -->
        <div class="card">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Key Phrases</h3>
            <ul class="space-y-2">
    """

        if key_phrases:
            for phrase in key_phrases[:10]:  # Limit to top 10
                phrase_text = phrase if isinstance(phrase, str) else phrase.get("text", "")
                html += f'<li class="flex items-start space-x-2"><i class="fas fa-tag text-joy-teal mt-1"></i><span class="text-gray-700 dark:text-gray-300">{phrase_text}</span></li>'
        else:
            html += '<li class="text-gray-600 dark:text-gray-400">No key phrases available</li>'

        html += """
            </ul>
        </div>

        <!-- Entities -->
        <div class="card">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">Entities</h3>
            <div class="flex flex-wrap gap-2">
    """

        if entities:
            for entity in entities[:15]:  # Limit to top 15
                entity_text = entity if isinstance(entity, str) else entity.get("text", "")
                html += f'<span class="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm text-gray-700 dark:text-gray-300">{entity_text}</span>'
        else:
            html += '<p class="text-gray-600 dark:text-gray-400">No entities identified</p>'

        html += """
            </div>
        </div>
    </div>
    """

        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Failed to get document analysis: {e}", exc_info=True)
        return HTMLResponse(
            content='<div class="card"><p class="text-red-600">Failed to load analysis</p></div>',
            status_code=500,
        )


@router.get("/api/document/{document_id}/actions", response_class=HTMLResponse)
async def get_document_actions(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns document action items tab HTML
    Lazy-loaded when user clicks Action Items tab
    """
    try:
        # Get document
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            return HTMLResponse(
                content="""
            <div class="card">
                <p class="text-red-600 dark:text-red-400">Document not found</p>
            </div>
        """
            )

        document = documents[0]
        action_items = document.get("action_items", [])

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

        for idx, item in enumerate(action_items):
            # Extract action item details
            if isinstance(item, str):
                item_text = item
                priority = "medium"
            else:
                item_text = item.get("text", item.get("title", ""))
                priority = item.get("priority", "medium")

            # Priority badge
            priority_class = {
                "high": "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
                "medium": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
                "low": "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
            }.get(priority, "bg-gray-100")

            html += f"""
        <div class="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <input type="checkbox"
                   class="mt-1 rounded border-gray-300 text-joy-teal focus:ring-joy-teal">
            <div class="flex-1">
                <div class="flex items-start justify-between">
                    <p class="font-medium text-gray-900 dark:text-white">{item_text}</p>
                    <span class="ml-2 px-2 py-1 rounded text-xs font-medium {priority_class}">
                        {priority}
                    </span>
                </div>
            </div>
        </div>
        """

        html += "</div></div>"

        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Failed to get document actions: {e}", exc_info=True)
        return HTMLResponse(
            content='<div class="card"><p class="text-red-600">Failed to load action items</p></div>',
            status_code=500,
        )


@router.get("/api/processing/status", response_class=HTMLResponse)
async def get_processing_status(current_user: UserInDB = Depends(get_current_user)):
    """
    Returns processing status HTML
    Shows documents currently being processed
    """
    try:
        processing_docs = await execute_select(
            "documents",
            match={"user_id": current_user.id, "status": "processing"},
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
            metadata = doc.get("processing_metadata", {})
            progress = metadata.get("progress", 50)
            current_step = metadata.get("current_step", "Processing")

            html_parts.append(
                f"""
        <div class="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg" data-document-id="{doc["id"]}">
            <div class="flex items-center justify-between mb-2">
                <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{doc["filename"]}</p>
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

    except Exception as e:
        logger.error(f"Failed to get processing status: {e}", exc_info=True)
        return HTMLResponse(
            content='<p class="text-red-600">Failed to load processing status</p>',
            status_code=500,
        )


@router.get("/api/search/suggestions", response_class=JSONResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Returns search suggestions JSON
    Used for autocomplete in search bar
    """
    try:
        # Search for matching documents (simple text search)
        documents = await execute_select(
            "documents",
            match={"user_id": current_user.id},
        )

        # Filter by query
        matching_docs = [
            doc
            for doc in documents
            if q.lower() in doc.get("filename", "").lower()
        ][:5]

        suggestions = []
        for doc in matching_docs:
            created_at_str = "Unknown"
            if doc.get("created_at"):
                if isinstance(doc["created_at"], str):
                    try:
                        created_dt = datetime.fromisoformat(
                            doc["created_at"].replace("Z", "+00:00")
                        )
                        created_at_str = created_dt.strftime("%b %d, %Y")
                    except:
                        created_at_str = doc["created_at"]
                else:
                    created_at_str = doc["created_at"].strftime("%b %d, %Y")

            suggestions.append(
                {
                    "id": doc["id"],
                    "text": doc.get("filename", ""),
                    "source": f"{doc.get('file_type', 'unknown')} - {created_at_str}",
                }
            )

        return JSONResponse(content={"suggestions": suggestions})

    except Exception as e:
        logger.error(f"Failed to get search suggestions: {e}", exc_info=True)
        return JSONResponse(content={"suggestions": []})


@router.get("/api/search", response_class=JSONResponse)
async def search_documents(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Search documents and return results
    Returns JSON for Alpine.js to handle
    """
    try:
        # Get all documents for user
        documents = await execute_select(
            "documents",
            match={"user_id": current_user.id},
            order="created_at.desc",
        )

        # Simple text search in filename and extracted_text
        matching_docs = []
        for doc in documents:
            filename = doc.get("filename", "").lower()
            extracted_text = (doc.get("extracted_text") or "").lower()
            if q.lower() in filename or q.lower() in extracted_text:
                matching_docs.append(doc)

        total = len(matching_docs)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_docs = matching_docs[start:end]

        results = []
        for doc in paginated_docs:
            created_at_str = "Unknown"
            if doc.get("created_at"):
                if isinstance(doc["created_at"], str):
                    try:
                        created_dt = datetime.fromisoformat(
                            doc["created_at"].replace("Z", "+00:00")
                        )
                        created_at_str = created_dt.strftime("%b %d, %Y")
                    except:
                        created_at_str = doc["created_at"]
                else:
                    created_at_str = doc["created_at"].strftime("%b %d, %Y")

            excerpt = ""
            if doc.get("extracted_text"):
                excerpt = doc["extracted_text"][:200] + "..."

            results.append(
                {
                    "id": doc["id"],
                    "filename": doc.get("filename", ""),
                    "document_type": doc.get("file_type", "unknown"),
                    "status": doc.get("status", "uploaded"),
                    "created_at": created_at_str,
                    "excerpt": excerpt,
                    "tags": [],
                }
            )

        return JSONResponse(
            content={
                "results": results,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return JSONResponse(
            content={
                "results": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }
        )
