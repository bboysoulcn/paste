"""Paste API router."""

import markdown
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
from pygments.util import ClassNotFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Paste
from app.services.paste_service import (
    clean_expired,
    delete_paste,
    generate_id,
    get_paste,
    read_paste_content,
    save_paste,
)

router = APIRouter()
settings = get_settings()


@router.post("/")
async def upload_paste(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Upload a paste without a specific filename.

    Reads content from request body and generates a random ID.
    """
    content = await request.body()

    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=413, detail="File too large")

    if not content:
        raise HTTPException(status_code=400, detail="No content provided")

    paste = await save_paste(db, content)

    # Schedule cleanup of expired pastes
    background_tasks.add_task(clean_expired, db)

    base_url = str(request.base_url).rstrip('/')

    response_data = {
        "url": f"{base_url}/{paste.paste_id}",
        "raw_url": f"{base_url}/{paste.paste_id}",
        "id": paste.paste_id,
        "delete_token": paste.delete_token,
    }

    if paste.image_width and paste.image_height:
        response_data["width"] = paste.image_width
        response_data["height"] = paste.image_height

    return JSONResponse(
        content=response_data,
        headers={"X-Delete-Token": paste.delete_token},
    )


@router.post("/{filename}")
async def upload_paste_with_filename(
    filename: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Upload a paste with a specific filename.

    The filename includes extension which helps determine content type.
    """
    content = await request.body()

    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=413, detail="File too large")

    if not content:
        raise HTTPException(status_code=400, detail="No content provided")

    # Use filename without extension as paste_id if it matches pattern
    paste_id = None
    if '.' in filename:
        base_name = filename.rsplit('.', 1)[0]
        if base_name.isalnum() or '-' in base_name or '_' in base_name:
            paste_id = base_name

    paste = await save_paste(db, content, filename, paste_id)

    # Schedule cleanup of expired pastes
    background_tasks.add_task(clean_expired, db)

    base_url = str(request.base_url).rstrip('/')

    response_data = {
        "url": f"{base_url}/{paste.paste_id}",
        "raw_url": f"{base_url}/{paste.paste_id}",
        "id": paste.paste_id,
        "filename": filename,
        "delete_token": paste.delete_token,
    }

    if paste.image_width and paste.image_height:
        response_data["width"] = paste.image_width
        response_data["height"] = paste.image_height

    return JSONResponse(
        content=response_data,
        headers={"X-Delete-Token": paste.delete_token},
    )


@router.get("/{paste_id}")
async def get_paste_content(
    paste_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Retrieve a paste by ID.

    Returns content with appropriate Content-Type.
    For markdown files, returns HTML if requested by browser.
    """
    paste = await get_paste(db, paste_id)

    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found")

    if paste.is_expired:
        raise HTTPException(status_code=410, detail="Paste has expired")

    content = read_paste_content(paste)

    # Handle markdown files
    if paste.is_markdown:
        accept = request.headers.get("Accept", "")
        if "text/html" in accept:
            # Return rendered HTML for browsers
            html_content = render_markdown(content.decode('utf-8'))
            return HTMLResponse(content=html_content)
        else:
            # Return raw markdown for curl/CLI
            return Response(content=content, media_type="text/markdown")

    # Return content with detected content type
    return Response(content=content, media_type=paste.content_type)


@router.delete("/{paste_id}")
async def delete_paste_endpoint(
    paste_id: str,
    x_delete_token: str = Header(..., alias="X-Delete-Token"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete a paste by ID.

    Requires valid delete token in X-Delete-Token header.
    """
    success = await delete_paste(db, paste_id, x_delete_token)

    if not success:
        raise HTTPException(status_code=404, detail="Paste not found or invalid token")

    return JSONResponse(content={"status": "deleted"})


@router.get("/{paste_id}/info")
async def get_paste_info(
    paste_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get metadata about a paste.

    Returns JSON with all paste information.
    """
    paste = await get_paste(db, paste_id)

    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found")

    return JSONResponse(
        content={
            "id": paste.paste_id,
            "filename": paste.filename,
            "content_type": paste.content_type,
            "file_size": paste.file_size,
            "image_width": paste.image_width,
            "image_height": paste.image_height,
            "expires_at": paste.expires_at.isoformat(),
            "created_at": paste.created_at.isoformat(),
            "is_expired": paste.is_expired,
            "is_image": paste.is_image,
            "is_markdown": paste.is_markdown,
        }
    )


def render_markdown(text: str) -> str:
    """
    Render markdown text to HTML with syntax highlighting.

    Args:
        text: Markdown text

    Returns:
        HTML string
    """
    # Convert markdown to HTML
    html = markdown.markdown(
        text,
        extensions=['fenced_code', 'nl2br', 'sane_lists']
    )

    # Wrap in template
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paste</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background: #fff;
        }}
        pre {{
            background: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
        }}
        code {{
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 14px;
        }}
        .highlight {{
            background: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        .highlight .hll {{ background-color: #ffffcc }}
        .highlight .c {{ color: #999988; font-style: italic }}
        .highlight .err {{ color: #a61717; background-color: #e3d2d2 }}
        .highlight .k {{ color: #000000; font-weight: bold }}
        .highlight .o {{ color: #000000; font-weight: bold }}
        .highlight .cm {{ color: #999988; font-style: italic }}
        .highlight .cp {{ color: #999999; font-weight: bold }}
        .highlight .c1 {{ color: #999988; font-style: italic }}
        .highlight .cs {{ color: #999999; font-weight: bold; font-style: italic }}
        .highlight .gd {{ color: #000000; background-color: #ffdddd }}
        .highlight .ge {{ color: #000000; font-style: italic }}
        .highlight .gr {{ color: #aa0000 }}
        .highlight .gh {{ color: #999999 }}
        .highlight .gi {{ color: #000000; background-color: #ddffdd }}
        .highlight .go {{ color: #888888 }}
        .highlight .gp {{ color: #555555 }}
        .highlight .gs {{ font-weight: bold }}
        .highlight .gu {{ color: #aaaaaa }}
        .highlight .gt {{ color: #aa0000 }}
        .highlight .kc {{ color: #000000; font-weight: bold }}
        .highlight .kd {{ color: #000000; font-weight: bold }}
        .highlight .kn {{ color: #000000; font-weight: bold }}
        .highlight .kp {{ color: #000000; font-weight: bold }}
        .highlight .kr {{ color: #000000; font-weight: bold }}
        .highlight .kt {{ color: #445588; font-weight: bold }}
        .highlight .m {{ color: #009999 }}
        .highlight .s {{ color: #d14 }}
        .highlight .na {{ color: #008080 }}
        .highlight .nb {{ color: #0086B3 }}
        .highlight .nc {{ color: #445588; font-weight: bold }}
        .highlight .no {{ color: #008080 }}
        .highlight .ni {{ color: #800080 }}
        .highlight .ne {{ color: #990000; font-weight: bold }}
        .highlight .nf {{ color: #990000; font-weight: bold }}
        .highlight .nn {{ color: #555555 }}
        .highlight .nt {{ color: #000080 }}
        .highlight .nv {{ color: #008080 }}
        .highlight .ow {{ color: #000000; font-weight: bold }}
        .highlight .w {{ color: #bbbbbb }}
        .highlight .mf {{ color: #009999 }}
        .highlight .mh {{ color: #009999 }}
        .highlight .mi {{ color: #009999 }}
        .highlight .mo {{ color: #009999 }}
        .highlight .sb {{ color: #d14 }}
        .highlight .sc {{ color: #d14 }}
        .highlight .sd {{ color: #d14 }}
        .highlight .s2 {{ color: #d14 }}
        .highlight .se {{ color: #d14 }}
        .highlight .sh {{ color: #d14 }}
        .highlight .si {{ color: #d14 }}
        .highlight .sx {{ color: #d14 }}
        .highlight .sr {{ color: #009926 }}
        .highlight .s1 {{ color: #d14 }}
        .highlight .ss {{ color: #990073 }}
        .highlight .bp {{ color: #999999 }}
        .highlight .vc {{ color: #008080 }}
        .highlight .vg {{ color: #008080 }}
        .highlight .vi {{ color: #008080 }}
        .highlight .il {{ color: #009999 }}
    </style>
</head>
<body>
    {html}
</body>
</html>"""
