# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user
import json
from unittest.mock import patch


@tagged('-at_install', 'post_install')
class TestBookmarkController(HttpCase):
    """Tests for bookmark controllers and HTTP routes"""

    def setUp(self):
        super().setUp()
        # Create test user with proper groups
        self.test_user = new_test_user(
            self.env,
            login='test_controller_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user'
        )

        # Create test bookmarks
        self.public_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Public Test Bookmark',
            'url': 'https://public-example.com',
            'description': 'This is a public bookmark',
            'is_public': True,
            'user_id': self.test_user.id
        })

        self.private_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Private Test Bookmark',
            'url': 'https://private-example.com',
            'description': 'This is a private bookmark',
            'is_public': False,
            'user_id': self.test_user.id
        })

        # Create test tags
        self.test_tag = self.env['odoo.bookmark.tag'].create({
            'name': 'test',
            'user_id': self.test_user.id
        })

    def test_public_bookmarks_page_loads(self):
        """Test that public bookmarks page loads correctly"""
        response = self.url_open('/bookmarks')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Public Test Bookmark', response.content)
        self.assertNotIn(b'Private Test Bookmark', response.content)

    def test_public_bookmarks_with_search(self):
        """Test public bookmarks page with search parameter"""
        response = self.url_open('/bookmarks?search=public')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Public Test Bookmark', response.content)

    def test_public_bookmarks_with_tag_filter(self):
        """Test public bookmarks page with tag filter"""
        # Add tag to public bookmark
        self.public_bookmark.tag_ids = [(6, 0, [self.test_tag.id])]

        response = self.url_open('/bookmarks?tag=test')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Public Test Bookmark', response.content)

    def test_bookmark_detail_page_public(self):
        """Test individual bookmark detail page for public bookmark"""
        response = self.url_open(f'/bookmarks/{self.public_bookmark.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Public Test Bookmark', response.content)

    def test_bookmark_detail_page_private_not_found(self):
        """Test that private bookmarks return 404 on detail page"""
        response = self.url_open(f'/bookmarks/{self.private_bookmark.id}')
        self.assertEqual(response.status_code, 404)

    def test_bookmark_detail_click_tracking(self):
        """Test that viewing bookmark detail increments click count"""
        initial_count = self.public_bookmark.click_count

        response = self.url_open(f'/bookmarks/{self.public_bookmark.id}')
        self.assertEqual(response.status_code, 200)
        
        # Check click count was incremented
        self.public_bookmark.refresh()
        self.assertEqual(self.public_bookmark.click_count, initial_count + 1)
        self.assertTrue(self.public_bookmark.last_clicked)

    def test_nonexistent_bookmark_404(self):
        """Test that nonexistent bookmark returns 404"""
        response = self.url_open('/bookmarks/99999')
        self.assertEqual(response.status_code, 404)


@tagged('standard', 'at_install')
class TestBookmarkAPI(HttpCase):
    """Tests for bookmark API endpoints"""

    def setUp(self):
        super().setUp()
        self.test_user = new_test_user(
            self.env,
            login='test_api_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user'
        )

    def test_api_add_bookmark_success(self):
        """Test successful bookmark creation via API"""
        self.authenticate('test_api_user', 'test_api_user')

        data = {
            'url': 'https://api-test.com',
            'title': 'API Test Bookmark',
            'description': 'Created via API',
            'tags': ['api', 'test']
        }

        response = self.url_open(
            '/api/bookmarks/add',
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get('success'))
        self.assertIn('id', response_data)

        # Verify bookmark was created
        bookmark = self.env['odoo.bookmark'].browse(response_data['id'])
        self.assertEqual(bookmark.name, 'API Test Bookmark')
        self.assertEqual(bookmark.url, 'https://api-test.com')
        self.assertEqual(len(bookmark.tag_ids), 2)

    def test_api_add_bookmark_missing_required_fields(self):
        """Test API bookmark creation with missing required fields"""
        self.authenticate('test_api_user', 'test_api_user')

        # Missing title
        data = {
            'url': 'https://api-test.com',
            'description': 'Missing title'
        }

        response = self.url_open(
            '/api/bookmarks/add',
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )

        response_data = json.loads(response.content)
        self.assertFalse(response_data.get('success'))
        self.assertIn('error', response_data)

    def test_api_add_bookmark_creates_tags(self):
        """Test that API creates new tags when they don't exist"""
        self.authenticate('test_api_user', 'test_api_user')

        # Verify tag doesn't exist initially
        existing_tag = self.env['odoo.bookmark.tag'].search([
            ('name', '=', 'newtag'),
            ('user_id', '=', self.test_user.id)
        ])
        self.assertFalse(existing_tag.exists())

        data = {
            'url': 'https://api-test.com',
            'title': 'API Test Bookmark',
            'tags': ['newtag']
        }

        response = self.url_open(
            '/api/bookmarks/add',
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )

        response_data = json.loads(response.content)
        self.assertTrue(response_data.get('success'))

        # Verify tag was created
        new_tag = self.env['odoo.bookmark.tag'].search([
            ('name', '=', 'newtag'),
            ('user_id', '=', self.test_user.id)
        ])
        self.assertTrue(new_tag.exists())

    def test_api_unauthorized_access(self):
        """Test API access without authentication"""
        data = {
            'url': 'https://api-test.com',
            'title': 'Unauthorized Test'
        }

        response = self.url_open(
            '/api/bookmarks/add',
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )

        # Should return error for unauthorized access
        self.assertNotEqual(response.status_code, 200)


@tagged('-at_install', 'post_install')
class TestArchiveController(HttpCase):
    """Tests for archive functionality"""

    def setUp(self):
        super().setUp()
        self.test_user = new_test_user(
            self.env,
            login='test_archive_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user'
        )

        self.test_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Archive Test Bookmark',
            'url': 'https://archive-test.com',
            'user_id': self.test_user.id
        })

    @patch('requests.get')
    def test_archive_page_success(self, mock_get):
        """Test successful page archiving"""
        # Mock the HTTP request
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.text = '<html><body>Test content</body></html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status.return_value = None

        self.authenticate('test_archive_user', 'test_archive_user')

        response = self.url_open(f'/bookmarks/archive/{self.test_bookmark.id}')

        # Should redirect back to bookmark form
        self.assertEqual(response.status_code, 200)

        # Verify content was archived
        self.test_bookmark.refresh()
        self.assertTrue(self.test_bookmark.archived_content)
        self.assertTrue(self.test_bookmark.archived_date)
        self.assertTrue(self.test_bookmark.has_archive)

    def test_archive_unauthorized_bookmark(self):
        """Test archiving bookmark owned by another user"""
        other_user = new_test_user(
            self.env,
            login='other_user',
            groups='base.group_user'
        )

        other_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Other User Bookmark',
            'url': 'https://other-test.com',
            'user_id': other_user.id
        })

        self.authenticate('test_archive_user', 'test_archive_user')

        response = self.url_open(f'/bookmarks/archive/{other_bookmark.id}')
        self.assertEqual(response.status_code, 404)

    def test_archive_nonexistent_bookmark(self):
        """Test archiving nonexistent bookmark"""
        self.authenticate('test_archive_user', 'test_archive_user')

        response = self.url_open('/bookmarks/archive/99999')
        self.assertEqual(response.status_code, 404)

    @patch('requests.get')
    def test_archive_request_failure(self, mock_get):
        """Test archive when HTTP request fails"""
        # Mock failed request
        mock_get.side_effect = Exception("Connection failed")

        self.authenticate('test_archive_user', 'test_archive_user')

        response = self.url_open(f'/bookmarks/archive/{self.test_bookmark.id}')

        # Should still redirect but with error parameter
        self.assertEqual(response.status_code, 200)

        # Verify no content was archived
        self.test_bookmark.refresh()
        self.assertFalse(self.test_bookmark.archived_content)
