from odoo import http
from odoo.http import request
import json
import requests
from datetime import datetime
import base64
import logging
import io
from PIL import Image
from odoo import fields
_logger = logging.getLogger(__name__)

class BookmarkController(http.Controller):
    
    @http.route('/api/bookmarks/add', type='json', auth='user')
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
    
    @http.route('/bookmarks', type='http', auth='public', website=True)
    def public_bookmarks(self, tag=None, search=None, page=1, **kw):
        """Public page for bookmarks"""
        page = int(page)
        per_page = 20
        
        domain = [('is_public', '=', True)]
        
        if tag:
            domain.append(('tag_ids.name', '=', tag))
        
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('description', 'ilike', search))
        
        bookmark_count = request.env['odoo.bookmark'].sudo().search_count(domain)
        
        pager = request.website.pager(
            url='/bookmarks',
            url_args={'tag': tag, 'search': search},
            total=bookmark_count,
            page=page,
            step=per_page,
        )
        
        bookmarks = request.env['odoo.bookmark'].sudo().search(
            domain, limit=per_page, offset=pager['offset'], order='create_date desc'
        )
        
        # Get all tags for filter
        all_tags = request.env['odoo.bookmark.tag'].sudo().search([
            ('id', 'in', request.env['odoo.bookmark'].sudo().search([
                ('is_public', '=', True)
            ]).mapped('tag_ids').ids)
        ])
        
        return request.render('shaarli_odoo.public_bookmarks', {
            'bookmarks': bookmarks,
            'tags': all_tags,
            'current_tag': tag,
            'search_query': search,
            'pager': pager,
        })

    @http.route('/bookmarks/<int:bookmark_id>', type='http', auth='public', website=True)
    def public_bookmark_detail(self, bookmark_id, **kw):
        """Public page for a single bookmark"""
        bookmark = request.env['odoo.bookmark'].sudo().browse(bookmark_id)
        
        if not bookmark.exists() or not bookmark.is_public:
            return request.not_found()
        
        # Increment view count
        bookmark.sudo().click_count += 1
        bookmark.sudo().last_clicked = fields.Datetime.now()
        
        return request.render('shaarli_odoo.public_bookmark_detail', {
            'bookmark': bookmark,
        })
    
    @http.route('/bookmarks/archive/<int:bookmark_id>', type='http', auth='user')
    def archive_page(self, bookmark_id, **kw):
        """Archive a webpage"""
        bookmark = request.env['odoo.bookmark'].browse(bookmark_id)
        
        if not bookmark.exists():
            return request.not_found()
            
        bookmark.ensure_one()
        
        # Ensure the user has access to this bookmark
        if request.env.user.id != bookmark.user_id.id and not request.env.user.has_group('base.group_system'):
            return request.not_found()
            
        # Archive the page
        try:
            self._archive_webpage(bookmark)
            return request.redirect(f'/web#id={bookmark_id}&model=odoo.bookmark&view_type=form')
        except Exception as e:
            _logger.error(f"Failed to archive page: {e}")
            return request.redirect(f'/web#id={bookmark_id}&model=odoo.bookmark&view_type=form&error=archive_failed')
    
    def _archive_webpage(self, bookmark):
        """Archive a webpage content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; Odoo Bookmarks/1.0; +http://yourwebsite.com)'
            }
            response = requests.get(bookmark.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Extract favicon if available
            favicon = None
            try:
                favicon_response = requests.get(f"https://www.google.com/s2/favicons?domain={bookmark.domain}", 
                                             headers=headers, timeout=5)
                if favicon_response.status_code == 200:
                    favicon = base64.b64encode(favicon_response.content)
            except Exception as e:
                _logger.warning(f"Failed to fetch favicon: {e}")
            
            # Try to take a screenshot or thumbnail (simplified)
            thumbnail = None
            
            # Save the archived content
            bookmark.write({
                'archived_content': response.text,
                'archived_date': fields.Datetime.now(),
                'favicon': favicon,
                'thumbnail': thumbnail,
                'content_type': response.headers.get('Content-Type', 'text/html'),
            })
            
            return True
        except Exception as e:
            _logger.error(f"Failed to archive page: {e}")
            raise
    
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