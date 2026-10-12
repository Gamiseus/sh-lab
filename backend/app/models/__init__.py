# sh_lab Models Package
# Export all models for easy importing

from app.models.game import (
    Game, GameBase, GameCreate, GameUpdate, GameRead
)

from app.models.user import (
    User, UserBase, UserCreate, UserUpdate, UserPasswordUpdate,
    UserRead, UserReadPrivate, UserSession, UserSettings
)

from app.models.review import (
    Review, ReviewBase, ReviewCreate, ReviewUpdate, 
    ReviewRead, ReviewReadWithUser
)

from app.models.news import (
    NewsPost, NewsPostBase, NewsPostCreate, NewsPostUpdate,
    NewsPostRead, NewsPostReadWithAuthor
)

from app.models.request import (
    GameRequest, GameRequestBase, GameRequestCreate, GameRequestUpdate,
    GameRequestRead, GameRequestReadAdmin
)

from app.models.config import (
    SystemConfig, SystemConfigRead, SystemConfigUpdate,
    get_config_bool, get_config_int
)

from app.models.social import (
    UserPlaytime, UserPlaytimeRead, UserPlaytimeUpdate,
    Friendship, FriendshipCreate, FriendshipUpdate, 
    FriendshipRead, FriendRead
)

from app.models.library import (
    UserLibrary, UserLibraryEntry, ServerGameCache
)

__all__ = [
    # Game
    "Game", "GameBase", "GameCreate", "GameUpdate", "GameRead",
    # User
    "User", "UserBase", "UserCreate", "UserUpdate", "UserPasswordUpdate",
    "UserRead", "UserReadPrivate", "UserSession", "UserSettings",
    # Review
    "Review", "ReviewBase", "ReviewCreate", "ReviewUpdate",
    "ReviewRead", "ReviewReadWithUser",
    # News
    "NewsPost", "NewsPostBase", "NewsPostCreate", "NewsPostUpdate",
    "NewsPostRead", "NewsPostReadWithAuthor",
    # Request
    "GameRequest", "GameRequestBase", "GameRequestCreate", "GameRequestUpdate",
    "GameRequestRead", "GameRequestReadAdmin",
    # Config
    "SystemConfig", "SystemConfigRead", "SystemConfigUpdate",
    "get_config_bool", "get_config_int",
    # Social
    "UserPlaytime", "UserPlaytimeRead", "UserPlaytimeUpdate",
    "Friendship", "FriendshipCreate", "FriendshipUpdate",
    "FriendshipRead", "FriendRead",
    # Library & Cache
    "UserLibrary", "UserLibraryEntry", "ServerGameCache",
]
