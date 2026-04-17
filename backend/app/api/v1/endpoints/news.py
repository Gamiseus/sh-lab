"""
News API Endpoints
"""
import os
import shutil
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlmodel import Session, select, func
from sqlalchemy import desc

from app.core.db import get_session
from app.core.auth import get_current_user, require_admin
from app.models.user import User
from app.models.news import NewsPost, NewsPostCreate, NewsPostUpdate, NewsPostReadWithAuthor

router = APIRouter()

# ============================================================
# Admin Endpoints
# ============================================================

@router.get("/admin/all", response_model=List[NewsPostReadWithAuthor])
async def get_all_news_admin(
    page: int = 1, 
    limit: int = 50,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Get all news posts (including drafts).
    """
    offset = (page - 1) * limit
    
    statement = (
        select(NewsPost, User)
        .join(User, User.id == NewsPost.author_id, isouter=True)
        .order_by(desc(NewsPost.created_at))
        .offset(offset).limit(limit)
    )
    
    results = session.exec(statement).all()
    
    return [
        NewsPostReadWithAuthor(
            **post.model_dump(),
            author_username=user.username if user else "Deleted User",
            author_display_name=user.display_name if user else None
        )
        for post, user in results
    ]

@router.get("/admin/images")
async def list_admin_images(
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: List shared/preset images in the admin folder.
    """
    directory = "/data/server/news/admin"
    # Create if not exists
    os.makedirs(directory, exist_ok=True)
    
    images = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            images.append({
                "filename": filename,
                "url": f"/server/news/admin/{filename}"
            })
            
    return images


# ============================================================
# Public Endpoints
# ============================================================

@router.get("", response_model=List[NewsPostReadWithAuthor])
async def get_news_posts(
    page: int = 1,
    limit: int = 20,
    tag: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Get published news posts.
    """
    offset = (page - 1) * limit
    
    # Base query joining author
    statement = (
        select(NewsPost, User)
        .join(User, User.id == NewsPost.author_id, isouter=True)
        .where(NewsPost.is_published == True)
    )
    
    # Filter by tag if provided
    if tag:
        # PostgreSQL specific array contains check
        statement = statement.where(NewsPost.tags.contains([tag]))
        
    # Order by pinned first, then published date
    statement = statement.order_by(
        desc(NewsPost.is_pinned),
        desc(NewsPost.published_at)
    ).offset(offset).limit(limit)
    
    results = session.exec(statement).all()
    
    return [
        NewsPostReadWithAuthor(
            **post.model_dump(),
            author_username=user.username if user else "Deleted User",
            author_display_name=user.display_name if user else None
        )
        for post, user in results
    ]

@router.get("/{post_id}", response_model=NewsPostReadWithAuthor)
async def get_news_post(
    post_id: int,
    session: Session = Depends(get_session)
):
    """
    Get a single news post by ID.
    """
    statement = (
        select(NewsPost, User)
        .join(User, User.id == NewsPost.author_id, isouter=True)
        .where(NewsPost.id == post_id)
        .where(NewsPost.is_published == True)
    )
    
    result = session.exec(statement).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="News post not found")
        
    post, user = result
    
    return NewsPostReadWithAuthor(
        **post.model_dump(),
        author_username=user.username if user else "Deleted User",
        author_display_name=user.display_name if user else None
    )

# ============================================================
# Admin Endpoints
# ============================================================

@router.post("", response_model=NewsPostReadWithAuthor)
async def create_news_post(
    post_data: NewsPostCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Create a new news post.
    """
    post = NewsPost(
        **post_data.model_dump(),
        author_id=admin.id,
        is_published=False,  # Draft by default
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(post)
    session.commit()
    session.refresh(post)
    
    return NewsPostReadWithAuthor(
        **post.model_dump(),
        author_username=admin.username,
        author_display_name=admin.display_name
    )

@router.put("/{post_id}", response_model=NewsPostReadWithAuthor)
async def update_news_post(
    post_id: int,
    post_data: NewsPostUpdate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Update a news post.
    """
    post = session.get(NewsPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="News post not found")
        
    # Update fields
    post_dict = post_data.model_dump(exclude_unset=True)
    for key, value in post_dict.items():
        setattr(post, key, value)
        
    post.updated_at = datetime.now(timezone.utc)
    
    session.add(post)
    session.commit()
    session.refresh(post)
    
    # Fetch author info
    author = session.get(User, post.author_id)
    
    return NewsPostReadWithAuthor(
        **post.model_dump(),
        author_username=author.username if author else "Deleted User",
        author_display_name=author.display_name if author else None
    )

@router.post("/{post_id}/publish")
async def publish_news_post(
    post_id: int,
    publish: bool = True,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Publish or unpublish a news post.
    """
    post = session.get(NewsPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="News post not found")
        
    post.is_published = publish
    if publish and not post.published_at:
        post.published_at = datetime.now(timezone.utc)
        
    session.add(post)
    session.commit()
    
    return {"message": f"Post {'published' if publish else 'unpublished'}"}

@router.delete("/{post_id}")
async def delete_news_post(
    post_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Delete a news post.
    """
    post = session.get(NewsPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="News post not found")
        
    session.delete(post)
    session.commit()
    
    # Optional: Clean up images directory
    import shutil
    import os
    img_dir = f"/data/server/news/{post_id}"
    if os.path.exists(img_dir):
        shutil.rmtree(img_dir)
    
    return {"message": "News post deleted"}

# ============================================================
# Image Management Endpoints
# ============================================================

@router.post("/{post_id}/images")
async def upload_news_image(
    post_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: Upload an image for a specific news post.
    """
    post = session.get(NewsPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="News post not found")
        
    # Ensure directory exists
    directory = f"/data/server/news/{post_id}"
    os.makedirs(directory, exist_ok=True)
    
    # Save file
    # Sanitize filename to prevent directory traversal
    filename = os.path.basename(file.filename)
    file_path = os.path.join(directory, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Return the public URL
    # Mounted at /server -> /data/server
    public_url = f"/server/news/{post_id}/{filename}"
    
    return {"url": public_url, "filename": filename}

@router.get("/{post_id}/images")
async def list_news_images(
    post_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin)
):
    """
    Admin: List all images uploaded for a news post.
    """
    directory = f"/data/server/news/{post_id}"
    if not os.path.exists(directory):
        return []
        
    images = []
    for filename in os.listdir(directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            images.append({
                "filename": filename,
                "url": f"/server/news/{post_id}/{filename}"
            })
            
    return images


