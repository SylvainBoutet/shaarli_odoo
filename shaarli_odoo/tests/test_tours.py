# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, tagged

FAVICON_VALUE = 'aWNvbi1ieXRlcw=='  # base64 of b'icon-bytes'


@tagged('post_install', '-at_install')
class TestShaarliTours(HttpCase):
    """Browser tours on the public pages and the backend screens"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref('base.user_admin')
        cls.admin.name = 'Tour Owner'
        cls.tag = cls.env['odoo.bookmark.tag'].create({
            'name': 'tourtag',
            'color': 3,
            'user_id': cls.admin.id,
        })
        cls.public_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Tour Public Bookmark',
            'url': 'https://tour.example.com',
            'description': 'Shown on the public page',
            'is_public': True,
            'favicon': FAVICON_VALUE,
            'tag_ids': [(6, 0, cls.tag.ids)],
            'user_id': cls.admin.id,
        })
        cls.private_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Tour Private Bookmark',
            'url': 'https://tour.example.org/page',
            'is_public': False,
            'user_id': cls.admin.id,
        })

    def _mock_response(self, text='', content=b''):
        response = MagicMock()
        response.status_code = 200
        response.text = text
        response.content = content
        response.headers = {'Content-Type': 'text/html'}
        response.raise_for_status.return_value = None
        return response

    def test_public_tour(self):
        """Public page: links, tag filter, detail page, favicon"""
        self.start_tour('/bookmarks', 'shaarli_public_tour')

    def test_backend_tour(self):
        """Kanban, list with owner, archive from the form, breadcrumb"""
        page = self._mock_response('<p>Tour archived page</p>')
        favicon = self._mock_response(content=b'icon-bytes')
        with patch.object(self.registry['odoo.bookmark'], '_archive_http_get', side_effect=[page, favicon]):
            self.start_tour('/web#action=shaarli_odoo.action_bookmarks', 'shaarli_backend_tour', login='admin')
        self.assertTrue(self.private_bookmark.has_archive)

    def test_new_bookmark_tour(self):
        """No Open URL / Archive Page on an unsaved bookmark"""
        self.start_tour('/web#action=shaarli_odoo.action_bookmarks&view_type=form', 'shaarli_new_bookmark_tour', login='admin')
        bookmark = self.env['odoo.bookmark'].search([('name', '=', 'Tour New Bookmark')])
        self.assertEqual(bookmark.url, 'https://tour-new.example.com')

    def test_tags_tour(self):
        """Tag list: color label and owner column"""
        self.start_tour('/web#action=shaarli_odoo.action_bookmark_tags', 'shaarli_tags_tour', login='admin')
