Introduction
Introduction
The GOG Games Application Programming Interface allows you to interact with the site using HTTP requests and JSON responses to obtain data that would normally require a web browser and user interaction.

danger
To prevent abuse, all requests to API endpoints on the clearnet have rate a limit imposed. If the limit is exceeded, the IP will be blocked for 10 seconds and an HTTP code of 429 will be returned.

Next
Base URL

----------------

Base URL
Base URL
The base URL for all requests is: https://gog-games.to/api

tip
The Tor onion service may also be used: goggamespyi7b6ybpnpnlwhb4md6owgbijfsuj6z5hesqt3yfyz42rad.onion/api

Previous
Introduction
Next
Namespace

----------------

Namespace
Namespace
There are currently three namespaces in use:

web
private
donor
Previous
Base URL
Next
Authentication

----------------

Authentication
Authentication
The web namespace requires no authentication. It will accept any GET requests at the endpoints.

The private and donor namespaces require authentication. You must send X-API-Key: 1234 in the header of the request to authenticate successfully.

danger
The API key above is an example only and of course will not work.

Previous
Namespace
Next
Endpoints

----------------

EndpointsPublic
Public
Learn about the public endpoints.

📄️ Query Game
The query-game endpoint will return game details and file information for a single game. You must supply it with an id or slug.

📄️ All Games
The all-games endpoint will return all active games in the database.

📄️ Download MD5
The download-md5 endpoint will return a list of all items for a game with and their corresponding MD5 checksums. You must supply it with an id or slug.

📄️ Complete MD5
The complete-md5 endpoint will return a list of every game along with their items and corresponding MD5 checksums.

📄️ Recent Updates
The recent-updates endpoint will return all games that are currently set as new or updated in the database.

📄️ Recent Torrents
The recent-torrents endpoint will return the last 50 games that had torrents created. It is ordered from newest to oldest.

Previous
Endpoints
Next
Query Game

-----------------

Query Game
The query-game endpoint will return game details and file information for a single game. You must supply it with an id or slug.

info
The size for files is in bytes.

Sample request (by id)
curl -X GET https://gog-games.to/api/web/query-game/4

Sample request (by slug)
curl -X GET https://gog-games.to/api/web/query-game/freespace_expansion

Sample response
{
  "game_info": {
    "id": "4",
    "slug": "freespace_expansion",
    "title": "Descent: Freespace Battle Pack",
    "developer": "Volition",
    "publisher": "Interplay",
    "image": "58e9a905ef59d7a9882ccad71bd4af68c3288679c64d829b6e30ae32d7a2e953",
    "background": "72acc4b3e6c4d69d511fcd77a19141b49092578201ac9e439ac9e560c7a5c9d0",
    "gog_url": "https://www.gog.com/game/freespace_expansion",
    "is_indev": false,
    "last_update": null,
    "infohash": "248D0A1CD08284299DE78D5C1ED359BB46717D8C"
  },
  "files": [
    {
      "type": "game",
      "name": "setup_freespace_2.0.0.7.exe",
      "size": 854646384
    },
    {
      "type": "goodie",
      "name": "freespace_manual.zip",
      "size": 9609898
    },
    {
      "type": "goodie",
      "name": "freespace_refcard.zip",
      "size": 56275
    },
    {
      "type": "goodie",
      "name": "freespace_wallpaper.zip",
      "size": 6624146
    }
  ]
}

Sample error (not found)
{"message": "Error: Game not found"}

Sample error (no files)
caution
Take into consideration there could be no files listed currently.

{
  "game_info": {
    "id": "1",
    "slug": "fallout_classic",
    "title": "Fallout Classic",
    "developer": "Black Isle Studios",
    "publisher": "Bethesda Softworks LLC",
    "image": "0ef80c3dc9692710809e4adaf2fcd3348f9ede1f530af6182c2972c86238e71a",
    "background": "c56bad8b70314d26f24c8c83c4e5cd868d01febac500f2401ad44ed2c9a597be",
    "gog_url": "https://www.gog.com/game/fallout",
    "is_indev": false,
    "last_update": "2024-05-19T20:43:44.000000Z",
    "infohash": null
  },
  "files": []
}

Previous
Public
Next
All Games


EndpointsPublicAll Games
All Games
The all-games endpoint will return all active games in the database.

Sample request
curl -X GET https://gog-games.to/api/web/all-games

Sample response
[
  {
    "id": "1096313866",
    "slug": "140_game",
    "title": "140",
    "developer": "Carlsen Games",
    "publisher": "Carlsen Games",
    "image": "e2bcfd5f2a8052460af43020b5db0ab3c92c95c2ddcdfe8d62dbe4ed270503d4",
    "background": "fa24ab919f018e70eca4248c74e3c93e1e8cded0c97ef72a6f1c4bde3a0716d6",
    "gog_url": "https://www.gog.com/game/140_game",
    "is_indev": false,
    "last_update": "2019-10-23T14:08:33.000000Z",
    "infohash": null
  },
  {
    "id": "1743024042",
    "slug": "1428_shadows_over_silesia",
    "title": "1428: Shadows over Silesia",
    "developer": "KUBI Games",
    "publisher": "KUBI Games",
    "image": "aaeebb394d749fa6dcd923f88a0324163117e7d7ce70edd95efa6c411738bf09",
    "background": "421464f754f3d6b4be210b68d7941ab66261f0320978a013e92d9ed52dae5bce",
    "gog_url": "https://www.gog.com/game/1428_shadows_over_silesia",
    "is_indev": false,
    "last_update": "2024-03-18T04:19:55.000000Z",
    "infohash": null
  },
  ...and so on
]

caution
If you want to be sure data is up-to-date, use the GOG.com API. Please be aware some games do not have an entry.

Previous
Query Game
Next
Download MD5
Sample request
Sample response


EndpointsPublicDownload MD5
Download MD5
The download-md5 endpoint will return a list of all items for a game with and their corresponding MD5 checksums. You must supply it with an id or slug.

Sample request (by id)
curl -X GET https://gog-games.to/api/web/download-md5/1

Sample request (by slug)
curl -X GET https://gog-games.to/api/web/download-md5/fallout_classic

Sample response
cbbf7fbb000f14bdcae70d59e69f2c52  Fallout_Bible_gog.zip
40a3394fd9ae0c984dc719fa2723e9c0  fallout_arts.zip
849f8b75a72293de43b572c6b0dff4bf  fallout_avatars.zip
c17cd2543b155ffa01349ba698674f6d  fallout_manual.zip
fb2ea09415a8edf049ab388a60afbffe  fallout_pipboys_avatars.zip
42c10c13405caf6707ecb12a149ef7e8  fallout_refcard.zip
74d22b4925370d25b2fc32e0a3a39875  fallout_series_wallpaper.zip
1bed24b33c3f1fec99b5393309c0950f  fallout_soundtrack.zip
1dc05625be866e90ae509492ac965ddb  fallout_wallpaper.zip
47b7b3c059d92c0fd6db5881635277ea  setup_fallout_2.1.0.18.exe

Sample error
caution
A game may not have checksums created and added to the database yet.

{"message": "Error: MD5 missing"}

Previous
All Games
Next
Complete MD5


EndpointsPublicComplete MD5
Complete MD5
The complete-md5 endpoint will return a list of every game along with their items and corresponding MD5 checksums.

Sample request
curl -X GET https://gog-games.to/api/web/complete-md5

Sample response
75f694f6207780a84c36a45d5bc6ea6a  140_game/140_ost_flac.zip
2eadab6fd1fc5a5b4df8b0e1e3deeefc  140_game/140_ost_mp3.zip
d5bfde063f535fc1b4136ba8a04bd3d5  140_game/setup_140_10.10.2019_(33252).exe
f1dc6e08b7e1407e16037aab4af10527  1428_shadows_over_silesia/1428_shadows_over_silesia_bonus_stories.zip
f209ca1aeccae0985bc7fd4962a2587e  1428_shadows_over_silesia/1428_shadows_over_silesia_soundtrack_mp3.zip
915d056d473ef92d1041bbf81d8110e4  1428_shadows_over_silesia/setup_1428_shadows_over_silesia_1.0.34_(64bit)_(72947)-1.bin
bf09be8536ef979f07e90542c33ee1ab  1428_shadows_over_silesia/setup_1428_shadows_over_silesia_1.0.34_(64bit)_(72947).exe
... and so on


Sample error
caution
An error will be returned if an MD5 file is missing for a game. All must be present for a response to be returned.

{"message": "Error: MD5 missing for 1428_shadows_over_silesia"}

Previous
Download MD5
Next
Recent Updates


EndpointsPublicRecent Updates
Recent Updates
The recent-updates endpoint will return all games that are currently set as new or updated in the database.

Sample request
curl -X GET https://gog-games.to/api/web/recent-updates

Sample response
[
  {
    "id": "3",
    "slug": "fallout_tactics_classic",
    "title": "Fallout Tactics Classic",
    "developer": "Micro Forté",
    "publisher": "Bethesda Softworks LLC",
    "image": "4f7a5f52b7618dc9f51ac95c4106182a3321053c381e9b4015a943856edffea4",
    "background": "36b667e12a68adc06c8fd03f8b89cbec4b90d5503a91692392592318984c8c3f",
    "gog_url": "https://www.gog.com/game/fallout_tactics",
    "is_indev": false,
    "last_update": "2024-05-19T20:43:46.000000Z",
    "infohash": null
  },
  {
    "id": "1",
    "slug": "fallout_classic",
    "title": "Fallout Classic",
    "developer": "Black Isle Studios",
    "publisher": "Bethesda Softworks LLC",
    "image": "0ef80c3dc9692710809e4adaf2fcd3348f9ede1f530af6182c2972c86238e71a",
    "background": "c56bad8b70314d26f24c8c83c4e5cd868d01febac500f2401ad44ed2c9a597be",
    "gog_url": "https://www.gog.com/game/fallout",
    "is_indev": false,
    "last_update": "2024-05-19T20:43:44.000000Z",
    "infohash": null
  },
  {
    "id": "2",
    "slug": "fallout_2_classic",
    "title": "Fallout 2 Classic",
    "developer": "Black Isle Studios",
    "publisher": "Bethesda Softworks LLC",
    "image": "e53d34bde0d96488b581a2e79fe3f9b25eabc9e51c990361443aa7b9c7660dd2",
    "background": "2405d078c16fc6b25414d2f08725596b955f5ca899ae30f317de7269dfefa22b",
    "gog_url": "https://www.gog.com/game/fallout_2",
    "is_indev": false,
    "last_update": "2024-05-19T20:43:44.000000Z",
    "infohash": null
  },
  ...and so on
]

Previous
Complete MD5
Next
Recent Torrents


EndpointsPublicRecent Torrents
Recent Torrents
The recent-torrents endpoint will return the last 50 games that had torrents created. It is ordered from newest to oldest.

info
You may construct the download URL for the torrent with the filename that is returned.

Such as: https://gog-games.to/downloads/torrents/torrent_filename

The Tor onion service may be used too.

warning
Torrent files are only kept for 30 days before being deleted to save space. You may use the infohash to generate a magnet link.

Sample request
curl -X GET https://gog-games.to/api/web/recent-torrents

Sample response
[
  {
    "id": "1",
    "slug": "fallout_classic",
    "title": "Fallout Classic",
    "developer": "Black Isle Studios",
    "publisher": "Bethesda Softworks LLC",
    "image": "0ef80c3dc9692710809e4adaf2fcd3348f9ede1f530af6182c2972c86238e71a",
    "background": "c56bad8b70314d26f24c8c83c4e5cd868d01febac500f2401ad44ed2c9a597be",
    "gog_url": "https://www.gog.com/game/fallout",
    "is_indev": false,
    "is_new": true,
    "is_updated": false,
    "last_update": "2024-05-16T02:40:21.000000Z",
    "torrent_date": "2024-05-16T02:43:09.000000Z",
    "torrent_filename": "fallout_classic_windows_gog_(2.1.0.18).torrent",
    "infohash": "905ce19bd2131f981d189c46443206739c3d6ed4"
  },
  ...and so on
]

Previous
Recent Updates
Next
Private