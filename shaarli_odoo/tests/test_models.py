# -*- coding: utf-8 -*-

import base64
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user



@tagged('post_install', '-at_install')
class TestBookmarkModel(TransactionCase):
    """Tests for the odoo.bookmark model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = new_test_user(
            cls.env,
            login='test_model_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.tag_python = cls.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'color': 1,
            'user_id': cls.test_user.id,
        })
        cls.tag_django = cls.env['odoo.bookmark.tag'].create({
            'name': 'django',
            'color': 2,
            'user_id': cls.test_user.id,
        })

    def _create(self, **vals):
        values = {
            'name': 'Test Bookmark',
            'url': 'https://example.com',
            'user_id': self.test_user.id,
        }
        values.update(vals)
        return self.env['odoo.bookmark'].create(values)

    def test_bookmark_creation_basic(self):
        """A bookmark keeps its values and is private by default"""
        bookmark = self._create(description='Test description')
        self.assertEqual(bookmark.name, 'Test Bookmark')
        self.assertEqual(bookmark.url, 'https://example.com')
        self.assertEqual(bookmark.description, 'Test description')
        self.assertEqual(bookmark.user_id, self.test_user)
        self.assertFalse(bookmark.is_public)
        self.assertEqual(bookmark.click_count, 0)
        self.assertFalse(bookmark.last_clicked)

    def test_bookmark_default_owner(self):
        """The owner defaults to the current user"""
        bookmark = self.env['odoo.bookmark'].with_user(self.test_user).create({
            'name': 'Owned Bookmark',
            'url': 'https://example.com',
        })
        self.assertEqual(bookmark.user_id, self.test_user)

    def test_bookmark_url_normalization_on_create(self):
        """https:// is added when the scheme is missing"""
        self.assertEqual(self._create(url='example.com').url, 'https://example.com')
        self.assertEqual(self._create(url='http://example.com').url, 'http://example.com')

    def test_bookmark_url_normalization_on_write(self):
        """https:// is added when the scheme is missing, on write too"""
        bookmark = self._create()
        bookmark.write({'url': 'odoo.com/page'})
        self.assertEqual(bookmark.url, 'https://odoo.com/page')

    def test_bookmark_domain_computation(self):
        """The domain is taken from the URL, without www."""
        self.assertEqual(self._create(url='https://www.github.com/user/repo').domain, 'github.com')
        self.assertEqual(self._create(url='http://subdomain.example.org/path').domain, 'subdomain.example.org')

    def test_bookmark_with_tags(self):
        """Tags are linked to the bookmark"""
        bookmark = self._create(tag_ids=[(6, 0, [self.tag_python.id, self.tag_django.id])])
        self.assertEqual(bookmark.tag_ids, self.tag_python | self.tag_django)

    def test_bookmark_archive_fields(self):
        """has_archive follows the archived content"""
        bookmark = self._create()
        self.assertFalse(bookmark.has_archive)
        bookmark.write({
            'archived_content': '<p>Test content</p>',
            'content_type': 'text/html',
        })
        self.assertTrue(bookmark.has_archive)

    def test_bookmark_action_open_url(self):
        """Opening the URL counts the click and returns a URL action"""
        bookmark = self._create()
        result = bookmark.action_open_url()
        self.assertEqual(bookmark.click_count, 1)
        self.assertTrue(bookmark.last_clicked)
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertEqual(result['url'], bookmark.url)
        self.assertEqual(result['target'], 'new')

    def _mock_response(self, text='', content=b''):
        response = MagicMock()
        response.status_code = 200
        response.text = text
        response.content = content
        response.headers = {'Content-Type': 'text/html'}
        response.raise_for_status.return_value = None
        return response

    def test_bookmark_action_archive_page(self):
        """The archive button stores the page and favicon, the form reloads"""
        bookmark = self._create()
        page = self._mock_response('<p>Archived body</p>')
        favicon = self._mock_response(content=b'icon-bytes')
        with patch.object(self.registry['odoo.bookmark'], '_archive_http_get', side_effect=[page, favicon]) as mock_get:
            self.assertTrue(bookmark.action_archive_page())
        self.assertEqual(mock_get.call_args_list[0].args[0], 'https://example.com')
        self.assertIn('Archived body', bookmark.archived_content)
        self.assertTrue(bookmark.archived_date)
        self.assertTrue(bookmark.has_archive)
        self.assertEqual(bookmark.content_type, 'text/html')
        self.assertEqual(base64.b64decode(bookmark.favicon), b'icon-bytes')

    def test_bookmark_action_archive_page_failure(self):
        """A network error is shown to the user and nothing is stored"""
        bookmark = self._create()
        with patch.object(self.registry['odoo.bookmark'], '_archive_http_get', side_effect=requests.ConnectionError('Connection failed')):
            with self.assertRaises(UserError):
                bookmark.action_archive_page()
        self.assertFalse(bookmark.has_archive)

    def test_bookmark_action_view_archive(self):
        """The archive is shown in its dedicated form view"""
        bookmark = self._create()
        result = bookmark.action_view_archive()
        self.assertEqual(result['res_model'], 'odoo.bookmark')
        self.assertEqual(result['res_id'], bookmark.id)
        self.assertEqual(result['view_id'], self.env.ref('shaarli_odoo.view_bookmark_archived_page_form').id)

    def test_bookmark_action_delete_archive(self):
        """Deleting the archive clears the archive fields"""
        bookmark = self._create(
            archived_content='<p>Archived</p>',
            content_type='text/html',
            archived_date='2026-01-01 10:00:00',
        )
        self.assertTrue(bookmark.has_archive)
        self.assertTrue(bookmark.action_delete_archive())
        self.assertFalse(bookmark.archived_content)
        self.assertFalse(bookmark.archived_date)
        self.assertFalse(bookmark.content_type)
        self.assertFalse(bookmark.has_archive)


@tagged('post_install', '-at_install')
class TestBookmarkTagModel(TransactionCase):
    """Tests for the odoo.bookmark.tag model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = new_test_user(
            cls.env,
            login='test_tag_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.user2 = new_test_user(
            cls.env,
            login='test_tag_user2',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )

    def test_tag_creation(self):
        """A tag keeps its values"""
        tag = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'color': 1,
            'user_id': self.test_user.id,
        })
        self.assertEqual(tag.name, 'python')
        self.assertEqual(tag.color, 1)
        self.assertEqual(tag.user_id, self.test_user)

    def test_tag_unique_name_per_user(self):
        """A user cannot own two tags with the same name"""
        self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.test_user.id})
        with self.assertRaises(ValidationError):
            self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.test_user.id})

    def test_tag_rename_to_existing_name(self):
        """Renaming a tag to a name the user already has is refused"""
        self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.test_user.id})
        tag = self.env['odoo.bookmark.tag'].create({'name': 'django', 'user_id': self.test_user.id})
        with self.assertRaises(ValidationError):
            tag.write({'name': 'python'})

    def test_tag_different_users_same_name(self):
        """Two users can own a tag with the same name"""
        tag1 = self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.test_user.id})
        tag2 = self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.user2.id})
        self.assertEqual(tag1.name, tag2.name)
        self.assertNotEqual(tag1.user_id, tag2.user_id)

    def test_tag_bookmark_count_computation(self):
        """bookmark_count counts the bookmarks holding the tag"""
        tag = self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.test_user.id})
        self.assertEqual(tag.bookmark_count, 0)
        self.env['odoo.bookmark'].create([{
            'name': 'Python Docs',
            'url': 'https://python.org',
            'tag_ids': [(6, 0, [tag.id])],
            'user_id': self.test_user.id,
        }, {
            'name': 'Python Tutorial',
            'url': 'https://tutorial.python.org',
            'tag_ids': [(6, 0, [tag.id])],
            'user_id': self.test_user.id,
        }])
        tag.invalidate_recordset(['bookmark_count'])
        self.assertEqual(tag.bookmark_count, 2)


@tagged('post_install', '-at_install')
class TestBookmarkIntegration(TransactionCase):
    """Bookmarks and tags together"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = new_test_user(
            cls.env,
            login='integration_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.user2 = new_test_user(
            cls.env,
            login='integration_user2',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )

    def test_bookmark_tag_relationship(self):
        """A bookmark is found through its tags"""
        tag_python = self.env['odoo.bookmark.tag'].create({'name': 'python', 'user_id': self.test_user.id})
        tag_web = self.env['odoo.bookmark.tag'].create({'name': 'web', 'user_id': self.test_user.id})
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Django Documentation',
            'url': 'https://docs.djangoproject.com',
            'tag_ids': [(6, 0, [tag_python.id, tag_web.id])],
            'user_id': self.test_user.id,
        })
        self.assertEqual(bookmark.tag_ids, tag_python | tag_web)
        self.assertIn(bookmark, self.env['odoo.bookmark'].search([('tag_ids', 'in', tag_python.id)]))

    def test_search_by_owner(self):
        """The owner filter returns the bookmarks of that owner only"""
        bookmark1 = self.env['odoo.bookmark'].create({
            'name': 'User 1 Bookmark', 'url': 'https://user1.com', 'user_id': self.test_user.id,
        })
        bookmark2 = self.env['odoo.bookmark'].create({
            'name': 'User 2 Bookmark', 'url': 'https://user2.com', 'user_id': self.user2.id,
        })
        user1_bookmarks = self.env['odoo.bookmark'].search([('user_id', '=', self.test_user.id)])
        self.assertIn(bookmark1, user1_bookmarks)
        self.assertNotIn(bookmark2, user1_bookmarks)

    def test_public_bookmark_visibility(self):
        """The public filter returns public bookmarks only"""
        private_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Private Bookmark', 'url': 'https://private.com',
            'is_public': False, 'user_id': self.test_user.id,
        })
        public_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Public Bookmark', 'url': 'https://public.com',
            'is_public': True, 'user_id': self.test_user.id,
        })
        public_bookmarks = self.env['odoo.bookmark'].search([('is_public', '=', True)])
        self.assertIn(public_bookmark, public_bookmarks)
        self.assertNotIn(private_bookmark, public_bookmarks)
