# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, tagged
from odoo.tests.common import JsonRpcException, new_test_user
from odoo.tools import mute_logger

REQUESTS_GET = 'odoo.addons.shaarli_odoo.controllers.main.requests.get'


@tagged('post_install', '-at_install')
class TestBookmarkController(HttpCase):
    """Tests for the public website pages"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Keep only the bookmarks of this test on the public page
        cls.env['odoo.bookmark'].search([('is_public', '=', True)]).write({'is_public': False})
        cls.test_user = new_test_user(
            cls.env,
            login='test_controller_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.test_tag = cls.env['odoo.bookmark.tag'].create({
            'name': 'testtag',
            'user_id': cls.test_user.id,
        })
        cls.public_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Public Test Bookmark',
            'url': 'https://public-example.com',
            'description': 'This is a public bookmark',
            'is_public': True,
            'user_id': cls.test_user.id,
        })
        cls.other_public_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Other Public Bookmark',
            'url': 'https://other-example.com',
            'description': 'Another public bookmark',
            'is_public': True,
            'user_id': cls.test_user.id,
        })
        cls.private_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Private Test Bookmark',
            'url': 'https://private-example.com',
            'description': 'This is a private bookmark',
            'is_public': False,
            'user_id': cls.test_user.id,
        })

    def test_public_bookmarks_page_loads(self):
        """The public page lists public bookmarks only"""
        response = self.url_open('/bookmarks')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Shared Bookmarks', response.content)
        self.assertIn(b'Public Test Bookmark', response.content)
        self.assertIn(b'Other Public Bookmark', response.content)
        self.assertNotIn(b'Private Test Bookmark', response.content)

    def test_public_bookmarks_with_search(self):
        """The search parameter filters on the title"""
        response = self.url_open('/bookmarks?search=other')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Other Public Bookmark', response.content)
        self.assertNotIn(b'Public Test Bookmark', response.content)

    def test_public_bookmarks_with_tag_filter(self):
        """The tag parameter filters on the tag name"""
        self.public_bookmark.tag_ids = [(6, 0, [self.test_tag.id])]
        response = self.url_open('/bookmarks?tag=testtag')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Public Test Bookmark', response.content)
        self.assertNotIn(b'Other Public Bookmark', response.content)

    def test_bookmark_detail_page_public(self):
        """The detail page of a public bookmark shows its data"""
        response = self.url_open(f'/bookmarks/{self.public_bookmark.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Public Test Bookmark', response.content)
        self.assertIn(b'https://public-example.com', response.content)
        self.assertIn(b'This is a public bookmark', response.content)

    def test_bookmark_detail_page_archive(self):
        """The detail page shows the archived copy of the page"""
        self.public_bookmark.write({
            'archived_content': '<p>Archived body</p>',
            'content_type': 'text/html',
        })
        response = self.url_open(f'/bookmarks/{self.public_bookmark.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Archived Version', response.content)

    def test_bookmark_detail_page_private_not_found(self):
        """A private bookmark has no public detail page"""
        response = self.url_open(f'/bookmarks/{self.private_bookmark.id}')
        self.assertEqual(response.status_code, 404)

    def test_bookmark_detail_click_tracking(self):
        """Viewing the detail page increments the click count"""
        initial_count = self.public_bookmark.click_count
        response = self.url_open(f'/bookmarks/{self.public_bookmark.id}')
        self.assertEqual(response.status_code, 200)
        self.public_bookmark.invalidate_recordset()
        self.assertEqual(self.public_bookmark.click_count, initial_count + 1)
        self.assertTrue(self.public_bookmark.last_clicked)

    def test_nonexistent_bookmark_404(self):
        """An unknown bookmark id returns 404"""
        missing_id = self.env['odoo.bookmark'].search([], order='id desc', limit=1).id + 1000
        response = self.url_open(f'/bookmarks/{missing_id}')
        self.assertEqual(response.status_code, 404)


@tagged('post_install', '-at_install')
class TestBookmarkAPI(HttpCase):
    """Tests for the JSON endpoint used by the browser extension"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = new_test_user(
            cls.env,
            login='test_api_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )

    def test_api_add_bookmark_success(self):
        """A bookmark is created with its tags"""
        self.authenticate('test_api_user', 'test_api_user')
        result = self.make_jsonrpc_request('/api/bookmarks/add', {
            'url': 'https://api-test.com',
            'title': 'API Test Bookmark',
            'description': 'Created via API',
            'tags': ['api', 'test'],
        })
        self.assertTrue(result['success'])
        bookmark = self.env['odoo.bookmark'].browse(result['id'])
        self.assertEqual(bookmark.name, 'API Test Bookmark')
        self.assertEqual(bookmark.url, 'https://api-test.com')
        self.assertEqual(bookmark.description, 'Created via API')
        self.assertEqual(bookmark.user_id, self.test_user)
        self.assertEqual(sorted(bookmark.tag_ids.mapped('name')), ['api', 'test'])

    def test_api_add_bookmark_missing_required_fields(self):
        """Without a title, nothing is created and an error is returned"""
        self.authenticate('test_api_user', 'test_api_user')
        count = self.env['odoo.bookmark'].search_count([])
        result = self.make_jsonrpc_request('/api/bookmarks/add', {
            'url': 'https://api-test.com',
            'description': 'Missing title',
        })
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'URL and title are required')
        self.assertEqual(self.env['odoo.bookmark'].search_count([]), count)

    def test_api_add_bookmark_reuses_and_creates_tags(self):
        """Existing tags of the user are reused, missing ones are created"""
        existing = self.env['odoo.bookmark.tag'].create({
            'name': 'existing',
            'user_id': self.test_user.id,
        })
        self.authenticate('test_api_user', 'test_api_user')
        result = self.make_jsonrpc_request('/api/bookmarks/add', {
            'url': 'https://api-test.com',
            'title': 'API Test Bookmark',
            'tags': ['existing', 'newtag'],
        })
        self.assertTrue(result['success'])
        bookmark = self.env['odoo.bookmark'].browse(result['id'])
        self.assertIn(existing, bookmark.tag_ids)
        new_tag = self.env['odoo.bookmark.tag'].search([
            ('name', '=', 'newtag'),
            ('user_id', '=', self.test_user.id),
        ])
        self.assertEqual(len(new_tag), 1)
        self.assertIn(new_tag, bookmark.tag_ids)

    def test_api_unauthorized_access(self):
        """Without a session, the endpoint refuses the call"""
        count = self.env['odoo.bookmark'].search_count([])
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/api/bookmarks/add', {
                'url': 'https://api-test.com',
                'title': 'Unauthorized Test',
            })
        self.assertEqual(self.env['odoo.bookmark'].search_count([]), count)


@tagged('post_install', '-at_install')
class TestArchiveController(HttpCase):
    """Tests for the page archiving route"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = new_test_user(
            cls.env,
            login='test_archive_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.test_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Archive Test Bookmark',
            'url': 'https://archive-test.com',
            'user_id': cls.test_user.id,
        })

    def _mock_response(self, text, content=b''):
        response = MagicMock()
        response.status_code = 200
        response.text = text
        response.content = content
        response.headers = {'Content-Type': 'text/html'}
        response.raise_for_status.return_value = None
        return response

    def test_archive_page_success(self):
        """The page content and favicon are stored on the bookmark"""
        page = self._mock_response('<html><body>Test content</body></html>')
        favicon = self._mock_response('', content=b'icon-bytes')
        self.authenticate('test_archive_user', 'test_archive_user')
        with patch(REQUESTS_GET, side_effect=[page, favicon]) as mock_get:
            response = self.url_open(f'/bookmarks/archive/{self.test_bookmark.id}', allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(mock_get.call_args_list[0].args[0], 'https://archive-test.com')
        self.test_bookmark.invalidate_recordset()
        # The Html field sanitizes the page: the text is kept
        self.assertIn('Test content', self.test_bookmark.archived_content)
        self.assertTrue(self.test_bookmark.archived_date)
        self.assertTrue(self.test_bookmark.has_archive)
        self.assertEqual(self.test_bookmark.content_type, 'text/html')
        self.assertTrue(self.test_bookmark.favicon)

    def test_archive_unauthorized_bookmark(self):
        """A user cannot archive the bookmark of another user"""
        other_user = new_test_user(
            self.env,
            login='other_archive_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        other_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Other User Bookmark',
            'url': 'https://other-test.com',
            'user_id': other_user.id,
        })
        self.authenticate('test_archive_user', 'test_archive_user')
        with patch(REQUESTS_GET) as mock_get:
            response = self.url_open(f'/bookmarks/archive/{other_bookmark.id}')
        self.assertEqual(response.status_code, 404)
        mock_get.assert_not_called()

    def test_archive_nonexistent_bookmark(self):
        """An unknown bookmark id returns 404"""
        missing_id = self.env['odoo.bookmark'].search([], order='id desc', limit=1).id + 1000
        self.authenticate('test_archive_user', 'test_archive_user')
        response = self.url_open(f'/bookmarks/archive/{missing_id}')
        self.assertEqual(response.status_code, 404)

    @mute_logger('odoo.addons.shaarli_odoo.controllers.main')
    def test_archive_request_failure(self):
        """A network failure redirects with an error and stores nothing"""
        self.authenticate('test_archive_user', 'test_archive_user')
        with patch(REQUESTS_GET, side_effect=Exception('Connection failed')):
            response = self.url_open(f'/bookmarks/archive/{self.test_bookmark.id}', allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn('error=archive_failed', response.headers['Location'])
        self.test_bookmark.invalidate_recordset()
        self.assertFalse(self.test_bookmark.archived_content)
