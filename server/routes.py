"""
API routes for the Web Content Analysis Bookmarklet System.
"""

from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from pydantic import BaseModel, HttpUrl

from server.models import RelevantChunk, WebContent, QueryRequest, SearchResult, AlignmentResult, CompareRequest

# Import services
from server.services.extractor import extract_content, complete_chunks
from server.services.llm_ollama import get_search_query
from server.services.retriever import search_urls
from server.services.comparator import calculate_alignment
from pathlib import Path

from server.utils import config
from server.utils.chunker import chunk_markdown, extract_complete_sentences
from server.utils.globals import BROWSER
from server.utils.nlp import markdown_to_plain_text, entity_extraction

from server.chunkers.embedding_clustering import select_diverse_german_chunks as select_diverse_german_chunks_embedding
from server.chunkers.tfidf_mmr import select_diverse_german_chunks as select_diverse_german_chunks_tfidf
from server.chunkers.graph_textrank import select_diverse_german_chunks as select_diverse_german_chunks_textrank

# Create routers for different functions
bookmarklet_router = APIRouter(tags=["Bookmarklet"])
extract_router = APIRouter(prefix="/api/extract", tags=["Extract"])
retrieve_router = APIRouter(prefix="/api/retrieve", tags=["Retrieve"])
compare_router = APIRouter(prefix="/api/compare", tags=["Compare"])
config_router = APIRouter(prefix="/api/config", tags=["Configuration"])


# Define model for URL configuration
class UrlConfig(BaseModel):
    urls: list[str]


# Get templates from app state
def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates

# Function to include all routers in an app
def include_routers(app):
    """Include all API routers in the FastAPI app."""
    app.include_router(bookmarklet_router)
    app.include_router(extract_router)
    app.include_router(retrieve_router)
    app.include_router(compare_router)
    app.include_router(config_router)


# Bookmarklet routes
@bookmarklet_router.get("/", response_class=HTMLResponse)
async def get_bookmarklet_page(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    """Serve the bookmarklet installation page."""
    return templates.TemplateResponse(
        # "bookmarklet.html",
        "bookmarklet_new.html",
        {"request": request, "title": "Web Content Analysis Bookmarklet"}
    )


@bookmarklet_router.get("/bookmarklet.js", response_class=Response)
async def get_bookmarklet_js(request: Request):
    """Serve the bookmarklet JavaScript code."""
    js_path = Path(__file__).parent / "bookmarklet.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="Bookmarklet JavaScript not found")

    with open(js_path, "r") as f:
        js_content = f.read()

    # Replace variables in the JavaScript
    host = "localhost"
    port = config.get("port", 5000)
    base_url = f"http://{host}:{port}"
    js_content = js_content.replace("__SERVER_BASE_URL__", base_url)

    return Response(content=js_content, media_type="application/javascript")


# Extract routes
@extract_router.post("/", response_model=list[RelevantChunk])
async def extract(content: WebContent, request: Request):
    """
    Extract and analyze content from a web page.

    1. Extract text content from HTML
    2. Chunk the content
    3. Identify relevant chunks
    4. Summarize the relevant chunks
    5. Return the relevant chunks with summaries
    """
    logger.info(f"Extracting content from: {content.url}")

    # Get context data
    context = {
        "url": str(content.url),
        "title": content.title,
        "author": content.author,
        "date": content.date
    }

    # Extract text from HTML
    extracted_content_md = extract_content(content.html)
    if not extracted_content_md:
        raise HTTPException(status_code=400, detail="Failed to extract content from HTML")

    # plain_text = markdown_to_plain_text(extracted_content_md)
    # entities = entity_extraction(plain_text)

    # Get the most relevant chunks
    chunks_md = chunk_markdown(extracted_content_md)
    complete_sentence_chunks = [
        extract_complete_sentences(markdown_to_plain_text(each_chunk))
        for each_chunk in chunks_md
        if len(each_chunk) > 250
    ]

    relevant_segments = select_diverse_german_chunks_embedding([each_chunk for each_chunk in complete_sentence_chunks], n=5)
    # relevant_segments = select_diverse_german_chunks_tfidf([each_chunk["content"] for each_chunk in chunks], n=5)
    # relevant_segments = select_diverse_german_chunks_textrank([each_chunk["content"] for each_chunk in chunks], n=5)
    relevant_chunks = list()
    for i, each_segment in enumerate(relevant_segments):
        each_chunk = {"content": each_segment, "id": str(i), "entities": {}, "importance": 1.0}
        relevant_chunks.append(each_chunk)

    # relevant_chunks_old = get_relevant_chunks(extracted_content_md, entities, context, 3)
    logger.info(f"Identified {len(relevant_chunks)} relevant chunks")

    # Summarize the relevant chunks
    model = config.get("model", "tulu3")
    ollama_host = config.get("ollama_host", "http://localhost:11434")

    chunks = await complete_chunks(relevant_chunks, context, model, ollama_host)
    return chunks


# Retrieve routes
@retrieve_router.post("/query", response_model=str)
async def generate_search_query(request: QueryRequest, req: Request):
    """Generate a search query for a specific chunk of content."""
    logger.info(f"Generating query for chunk: {request.chunk_id}")

    model = config.get("model", "tulu3")
    ollama_host = config.get("ollama_host", "http://localhost:11434")

    query = await get_search_query(request.chunk_content, request.context, model, ollama_host)
    query = query.strip("\"")
    logger.info(f"Generated query: \"{query}\"")

    return query


@retrieve_router.post("/search", response_model=list[SearchResult])
async def search(query: str = None, req: Request = None):
    """
    Perform a search with the generated query and return results.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")

    context = None

    # Check if query is provided either as a parameter or in the request body
    try:
        # Try to get query and context from request body if not provided as a parameter
        body = await req.json()
        context = body["context"]

    except Exception as e:
        # If JSON parsing fails, continue with what we have
        logger.error(f"Error parsing request body: {e}")

    logger.info(f"Searching for: {query}")

    # Get the final list of custom URLs
    custom_urls = config.get("custom_urls", list())
    original_url = context["url"]

    # If we have custom URLs, get site-specific results
    site_specific_results = list()
    for url in custom_urls:
        # Extract domain for site search
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        # Get results for this specific site
        site_results = await search_urls(query, engine="google_api", domain=domain, fallback=False)

        # Add to overall site-specific results
        site_specific_results.extend(site_results)

    # Combine general and site-specific results, removing duplicates
    combined_results = list()
    seen_urls = {HttpUrl(original_url)}

    # Get general search results
    general_results = await search_urls(query, engine="google_api", domain=None, fallback=False, max_results=3)

    # Add general results first then add site-specific results
    for result in general_results + site_specific_results:
        each_result = result.url
        if result.url not in seen_urls:
            seen_urls.add(each_result)
            combined_results.append(result)

    return combined_results


# Compare routes
@compare_router.post("/", response_model=AlignmentResult)
async def compare(request: CompareRequest, req: Request):
    """
    Compare original content with content from a search result URL.

    1. Fetch content from the URL
    2. Extract and chunk the content
    3. Calculate semantic alignment with the original chunk
    4. Return alignment score and explanation
    """
    logger.info(f"Comparing chunk {request.original_chunk.id} with {request.search_result_url}")

    model = config.get("model", "tulu3")
    ollama_host = config.get("ollama_host", "http://localhost:11434")

    # Calculate alignment
    alignment = await calculate_alignment(
        request.original_chunk.content,
        request.query,
        request.search_result_url,
        request.context,
        model,
        ollama_host
    )

    return alignment


# URL Configuration routes
@config_router.get("/urls", response_model=UrlConfig)
async def get_urls(request: Request):
    """Get custom search URLs from config."""
    custom_urls = config.get("custom_urls", [])
    return {"urls": custom_urls}


@config_router.post("/urls", response_model=UrlConfig)
async def set_urls(url_config: UrlConfig, request: Request):
    """Save custom search URLs to config."""

    config.set("custom_urls", url_config.urls)
    logger.info(f"Saved {len(url_config.urls)} custom URLs to config")

    return {"urls": config.get("custom_urls", list())}


@bookmarklet_router.get("/proxy", response_class=HTMLResponse)
async def proxy_url(request: Request, url: str = None):
    """
    Proxy endpoint that fetches HTML from the specified URL and serves it through
    the local server, avoiding mixed content issues.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    logger.info(f"Proxying content from: {url}")

    html_content = await BROWSER.get_html_content(url)
    if html_content.error:
        raise HTTPException(status_code=500, detail=f"Error fetching content: {html_content.error}")

    if not html_content.content:
        raise HTTPException(status_code=500, detail="No content fetched from the URL")

    # Add JavaScript alert to the HTML content
    alert_script = """
    <script>
        alert(
            "This is a proxy URL due to restrictions on the original page. " +
            "Please click the bookmarklet again. " +
            "Use the back button to return to the original page."
        );
    </script>
    """

    # Insert the alert script at the beginning of the HTML content
    html_content_modified = alert_script + html_content.content

    return HTMLResponse(content=html_content_modified, media_type="text/html")
