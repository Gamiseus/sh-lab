"""
Friends API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_, and_
from pydantic import BaseModel

from app.core.db import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.social import Friendship, FriendRead

router = APIRouter()

# ============================================================
# Response Schemas
# ============================================================

class FriendRequest(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    created_at: Optional[datetime]
    direction: str  # 'incoming' or 'outgoing'

class FriendData(BaseModel):
    id: int  # friendship id
    user_id: int  # friend's user id
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    since: Optional[datetime]

class FriendsListResponse(BaseModel):
    friends: List[FriendData]
    pending_incoming: int
    pending_outgoing: int

# ============================================================
# Friends Endpoints
# ============================================================

@router.get("", response_model=FriendsListResponse)
async def get_friends_list(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all accepted friends."""
    # Get accepted friendships where current user is either side
    statement = select(Friendship, User).where(
        Friendship.status == "accepted",
        or_(
            Friendship.user_id == current_user.id,
            Friendship.friend_id == current_user.id
        )
    ).join(
        User,
        or_(
            and_(Friendship.user_id == current_user.id, User.id == Friendship.friend_id),
            and_(Friendship.friend_id == current_user.id, User.id == Friendship.user_id)
        )
    )
    
    results = session.exec(statement).all()
    
    friends = []
    for friendship, friend_user in results:
        friends.append(FriendData(
            id=friendship.id,
            user_id=friend_user.id,
            username=friend_user.username,
            display_name=friend_user.display_name,
            avatar_url=friend_user.avatar_url,
            since=friendship.updated_at or friendship.created_at
        ))
    
    # Count pending requests
    pending_incoming = session.exec(
        select(Friendship).where(
            Friendship.friend_id == current_user.id,
            Friendship.status == "pending"
        )
    ).all()
    
    pending_outgoing = session.exec(
        select(Friendship).where(
            Friendship.user_id == current_user.id,
            Friendship.status == "pending"
        )
    ).all()
    
    return FriendsListResponse(
        friends=friends,
        pending_incoming=len(pending_incoming),
        pending_outgoing=len(pending_outgoing)
    )

@router.get("/requests", response_model=List[FriendRequest])
async def get_friend_requests(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all pending friend requests (both incoming and outgoing)."""
    requests = []
    
    # Incoming requests
    incoming = session.exec(
        select(Friendship, User)
        .where(
            Friendship.friend_id == current_user.id,
            Friendship.status == "pending"
        )
        .join(User, User.id == Friendship.user_id)
    ).all()
    
    for friendship, sender in incoming:
        requests.append(FriendRequest(
            id=friendship.id,
            user_id=sender.id,
            username=sender.username,
            display_name=sender.display_name,
            avatar_url=sender.avatar_url,
            created_at=friendship.created_at,
            direction="incoming"
        ))
    
    # Outgoing requests
    outgoing = session.exec(
        select(Friendship, User)
        .where(
            Friendship.user_id == current_user.id,
            Friendship.status == "pending"
        )
        .join(User, User.id == Friendship.friend_id)
    ).all()
    
    for friendship, recipient in outgoing:
        requests.append(FriendRequest(
            id=friendship.id,
            user_id=recipient.id,
            username=recipient.username,
            display_name=recipient.display_name,
            avatar_url=recipient.avatar_url,
            created_at=friendship.created_at,
            direction="outgoing"
        ))
    
    # Sort by date, newest first
    requests.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    
    return requests

@router.post("/request/{user_id}")
async def send_friend_request(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Send a friend request to another user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # Check target user exists
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for existing friendship/request
    existing = session.exec(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == user_id),
                and_(Friendship.user_id == user_id, Friendship.friend_id == current_user.id)
            )
        )
    ).first()
    
    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        elif existing.status == "pending":
            if existing.user_id == current_user.id:
                raise HTTPException(status_code=400, detail="Friend request already sent")
            else:
                # They sent us a request, auto-accept!
                existing.status = "accepted"
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
                session.commit()
                return {"message": "Friend request accepted (they had sent you one)", "status": "accepted"}
        elif existing.status == "blocked":
            raise HTTPException(status_code=400, detail="Cannot send friend request")
    
    # Create new friend request
    friendship = Friendship(
        user_id=current_user.id,
        friend_id=user_id,
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(friendship)
    session.commit()
    
    return {"message": "Friend request sent", "status": "pending"}

@router.post("/{friendship_id}/accept")
async def accept_friend_request(
    friendship_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Accept a friend request."""
    friendship = session.get(Friendship, friendship_id)
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    # Only the recipient can accept
    if friendship.friend_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot accept this request")
    
    if friendship.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    friendship.status = "accepted"
    friendship.updated_at = datetime.now(timezone.utc)
    
    session.add(friendship)
    session.commit()
    
    return {"message": "Friend request accepted"}

@router.post("/{friendship_id}/reject")
async def reject_friend_request(
    friendship_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Reject or cancel a friend request."""
    friendship = session.get(Friendship, friendship_id)
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    # Either party can reject/cancel
    if friendship.friend_id != current_user.id and friendship.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify this request")
    
    if friendship.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    session.delete(friendship)
    session.commit()
    
    return {"message": "Friend request rejected"}

@router.delete("/{friendship_id}")
async def remove_friend(
    friendship_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Remove a friend."""
    friendship = session.get(Friendship, friendship_id)
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")
    
    # Either party can unfriend
    if friendship.friend_id != current_user.id and friendship.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify this friendship")
    
    session.delete(friendship)
    session.commit()
    
    return {"message": "Friend removed"}
