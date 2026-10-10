# Shared Bookmarks

Save, tag and share web bookmarks in Odoo, publish the public ones on a website page and archive page content to read it later.

This repository contains the module `shaarli_odoo` for Odoo 20.0 (branch `20.0`).

## Features

- Bookmarks with title, URL, description, notes, color tags and an owner, private or public.
- Public bookmarks listed on the website at `/bookmarks`, with tag filter, search and pagination.
- Page archiving: the HTML of the bookmarked page is stored on the record. The domain is sent to the Google favicon service to fetch the site icon.
- Click counter and statistics by domain and month for bookmark managers.
- JSON-RPC route `/api/bookmarks/add` to add a bookmark from a script.

## Installation

1. Add this repository to the addons path.
2. Install **Shared Bookmarks** from the Apps menu (the Website app is installed with it).
3. Give users the *Bookmark User* or *Bookmark Manager* access.

## Tests

```bash
odoo-bin -d <database> -i shaarli_odoo --test-enable --test-tags /shaarli_odoo --stop-after-init
```

## License

LGPL-3, see [LICENSE](LICENSE).
