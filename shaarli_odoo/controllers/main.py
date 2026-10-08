import logging
from urllib.parse import urlencode

from odoo import _, fields, http  # noqa: F401
from odoo.http import request

_logger = logging.getLogger(__name__)


def _tag_url(tag_name):
    """URL of the public page filtered on a tag, with the name encoded"""
    return '/bookmarks?%s' % urlencode({'tag': tag_name})


class BookmarkController(http.Controller):

    @http.route('/api/bookmarks/add', type='jsonrpc', auth='user')
    def add_bookmark(self, **kw):
        """API endpoint for browser extension to add bookmarks"""
        url = kw.get('url')
        title = kw.get('title')
        description = kw.get('description', '')
        tags = kw.get('tags', [])

        if not url or not title:
            return {'success': False, 'error': 'URL and title are required'}

        # Create or find tags
        tag_ids = []
        for tag_name in tags:
            tag = request.env['odoo.bookmark.tag'].search([
                ('name', '=', tag_name),
                ('user_id', '=', request.env.user.id)
            ], limit=1)

            if not tag:
                tag = request.env['odoo.bookmark.tag'].create({
                    'name': tag_name,
                    'user_id': request.env.user.id
                })

            tag_ids.append(tag.id)

        # Create bookmark
        bookmark = request.env['odoo.bookmark'].create({
            'name': title,
            'url': url,
            'description': description,
            'tag_ids': [(6, 0, tag_ids)],
            'user_id': request.env.user.id
        })

        return {
            'success': True,
            'id': bookmark.id
        }

    @http.route([
        '/bookmarks',
        '/bookmarks/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def public_bookmarks(self, tag=None, search=None, page=1, **kw):
        """Public page for bookmarks"""
        # The pager clamps the page and ignores non-numeric values
        per_page = 20

        domain = [('is_public', '=', True)]

        if tag:
            domain.append(('tag_ids.name', '=', tag))

        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('description', 'ilike', search))

        bookmark_count = request.env['odoo.bookmark'].sudo().search_count(domain)

        # Prepare URL args, filtering out None values
        url_args = {}
        if tag:
            url_args['tag'] = tag
        if search:
            url_args['search'] = search

        pager = request.env.website.pager(
            url='/bookmarks',
            url_args=url_args,
            total=bookmark_count,
            page=page,
            step=per_page,
        )

        bookmarks = request.env['odoo.bookmark'].sudo().search(
            domain, limit=per_page, offset=pager['offset'], order='create_date desc'
        )

        # Get all tags for filter, one entry per name (tags are per user)
        all_tags = request.env['odoo.bookmark'].sudo().search([
            ('is_public', '=', True)
        ]).tag_ids.sorted('name')
        tag_by_name = {}
        for public_tag in all_tags:
            tag_by_name.setdefault(public_tag.name, public_tag)
        all_tags = all_tags.browse([t.id for t in tag_by_name.values()])

        return request.render('shaarli_odoo.public_bookmarks', {
            'bookmarks': bookmarks,
            'tags': all_tags,
            'current_tag': tag,
            'search_query': search,
            'pager': pager,
            'tag_url': _tag_url,
        })

    @http.route('/bookmarks/<int:bookmark_id>', type='http', auth='public', website=True, sitemap=False)
    def public_bookmark_detail(self, bookmark_id, **kw):
        """Public page for a single bookmark"""
        bookmark = request.env['odoo.bookmark'].sudo().browse(bookmark_id)

        if not bookmark.exists() or not bookmark.is_public:
            raise request.not_found()

        # Increment view count
        bookmark.sudo().click_count += 1
        bookmark.sudo().last_clicked = fields.Datetime.now()

        return request.render('shaarli_odoo.public_bookmark_detail', {
            'bookmark': bookmark,
            'tag_url': _tag_url,
        })

    @http.route('/bookmarks/archive/<int:bookmark_id>', type='http', auth='user')
    def archive_page(self, bookmark_id, **kw):
        """Archive a webpage"""
        bookmark = request.env['odoo.bookmark'].browse(bookmark_id)

        if not bookmark.exists():
            raise request.not_found()

        # Only the bookmarks the user may modify (record rules) can be archived
        if not bookmark.has_access('write'):
            raise request.not_found()

        # Archive the page
        try:
            bookmark._archive_webpage()
            return request.redirect(f'/odoo/action-shaarli_odoo.action_bookmarks/{bookmark_id}')
        except Exception as e:
            _logger.error("Failed to archive page: %s", e)
            return request.redirect(f'/odoo/action-shaarli_odoo.action_bookmarks/{bookmark_id}?error=archive_failed')

    # Dans controllers/main.py, ajoute ces fonctions

    def _get_tag_color(self, color_index):
        """Convert Odoo color index to CSS color"""
        colors = [
            '#F06050', '#F4A460', '#F7CD1F', '#6CC1ED', '#814968',
            '#EB7E7F', '#2C8397', '#475577', '#D6145F', '#30C381'
        ]
        return colors[color_index % len(colors)] if color_index is not None else '#6c757d'

    def _get_contrast_color(self, color_index):
        """Return white or black depending on background color"""
        colors = [
            '#FFFFFF', '#000000', '#000000', '#000000', '#FFFFFF',
            '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#000000'
        ]
        return colors[color_index % len(colors)] if color_index is not None else '#FFFFFF'
