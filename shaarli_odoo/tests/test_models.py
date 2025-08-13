# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
import re


@tagged('standard', 'at_install')
class TestBookmarkModel(TransactionCase):
    """Tests for odoo.bookmark model"""

    def setUp(self):
        super().setUp()
        # Create test user
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

        # Create test tags
        self.tag_python = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'color': 1,
            'user_id': self.test_user.id
        })
        self.tag_django = self.env['odoo.bookmark.tag'].create({
            'name': 'django',
            'color': 2,
            'user_id': self.test_user.id
        })

    def test_bookmark_creation_basic(self):
        """Test basic bookmark creation"""
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark',
            'url': 'https://example.com',
            'description': 'Test description',
            'user_id': self.test_user.id
        })

        self.assertTrue(bookmark.exists())
        self.assertEqual(bookmark.name, 'Test Bookmark')
        self.assertEqual(bookmark.url, 'https://example.com')
        self.assertEqual(bookmark.user_id, self.test_user)
        self.assertFalse(bookmark.is_public)  # Default is False

    def test_bookmark_url_normalization(self):
        """Test URL normalization (adding https://)"""
        # Test URL without protocol
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark',
            'url': 'example.com',
            'user_id': self.test_user.id
        })

        self.assertEqual(bookmark.url, 'https://example.com')

        # Test URL with http
        bookmark2 = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark 2',
            'url': 'http://example.com',
            'user_id': self.test_user.id
        })

        self.assertEqual(bookmark2.url, 'http://example.com')

    def test_bookmark_domain_computation(self):
        """Test domain field computation from URL"""
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark',
            'url': 'https://www.github.com/user/repo',
            'user_id': self.test_user.id
        })

        self.assertEqual(bookmark.domain, 'github.com')

        # Test with different URL formats
        bookmark2 = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark 2',
            'url': 'http://subdomain.example.org/path',
            'user_id': self.test_user.id
        })

        self.assertEqual(bookmark2.domain, 'subdomain.example.org')

    def test_bookmark_with_tags(self):
        """Test bookmark creation with tags"""
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Python Tutorial',
            'url': 'https://python.org',
            'tag_ids': [(6, 0, [self.tag_python.id, self.tag_django.id])],
            'user_id': self.test_user.id
        })

        self.assertEqual(len(bookmark.tag_ids), 2)
        self.assertIn(self.tag_python, bookmark.tag_ids)
        self.assertIn(self.tag_django, bookmark.tag_ids)

    def test_bookmark_archive_functionality(self):
        """Test archive-related fields and computations"""
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark',
            'url': 'https://example.com',
            'user_id': self.test_user.id
        })

        # Initially no archive
        self.assertFalse(bookmark.has_archive)
        self.assertFalse(bookmark.archived_content)

        # Add archived content
        bookmark.write({
            'archived_content': '<html><body>Test content</body></html>',
            'content_type': 'text/html'
        })

        self.assertTrue(bookmark.has_archive)

    def test_bookmark_click_tracking(self):
        """Test click count and last clicked tracking"""
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Test Bookmark',
            'url': 'https://example.com',
            'user_id': self.test_user.id
        })

        initial_count = bookmark.click_count
        self.assertEqual(initial_count, 0)

        # Simulate click
        result = bookmark.action_open_url()

        self.assertEqual(bookmark.click_count, initial_count + 1)
        self.assertTrue(bookmark.last_clicked)
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertEqual(result['url'], bookmark.url)

    def test_bookmark_required_fields(self):
        """Test required field validation"""
        # Test missing name
        with self.assertRaises(Exception):
            self.env['odoo.bookmark'].create({
                'url': 'https://example.com',
                'user_id': self.test_user.id
            })

        # Test missing URL
        with self.assertRaises(Exception):
            self.env['odoo.bookmark'].create({
                'name': 'Test Bookmark',
                'user_id': self.test_user.id
            })


@tagged('standard', 'at_install')
class TestBookmarkTagModel(TransactionCase):
    """Tests for odoo.bookmark.tag model"""

    def setUp(self):
        super().setUp()
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user_tag',
            'email': 'test_tag@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

    def test_tag_creation(self):
        """Test basic tag creation"""
        tag = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'color': 1,
            'user_id': self.test_user.id
        })

        self.assertTrue(tag.exists())
        self.assertEqual(tag.name, 'python')
        self.assertEqual(tag.color, 1)
        self.assertEqual(tag.user_id, self.test_user)

    def test_tag_unique_constraint(self):
        """Test unique constraint on tag name per user"""
        # Create first tag
        self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': self.test_user.id
        })

        # Try to create duplicate tag for same user - should fail
        with self.assertRaises(Exception):
            self.env['odoo.bookmark.tag'].create({
                'name': 'python',
                'user_id': self.test_user.id
            })

    def test_tag_different_users_same_name(self):
        """Test that different users can have tags with same name"""
        user2 = self.env['res.users'].create({
            'name': 'Test User 2',
            'login': 'test_user_2',
            'email': 'test2@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

        # Create tag for first user
        tag1 = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': self.test_user.id
        })

        # Create tag with same name for second user - should work
        tag2 = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': user2.id
        })

        self.assertTrue(tag1.exists())
        self.assertTrue(tag2.exists())
        self.assertEqual(tag1.name, tag2.name)
        self.assertNotEqual(tag1.user_id, tag2.user_id)

    def test_tag_bookmark_count_computation(self):
        """Test bookmark count computation for tags"""
        tag = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': self.test_user.id
        })

        # Initially no bookmarks
        self.assertEqual(tag.bookmark_count, 0)

        # Create bookmarks with this tag
        bookmark1 = self.env['odoo.bookmark'].create({
            'name': 'Python Docs',
            'url': 'https://python.org',
            'tag_ids': [(6, 0, [tag.id])],
            'user_id': self.test_user.id
        })

        bookmark2 = self.env['odoo.bookmark'].create({
            'name': 'Python Tutorial',
            'url': 'https://tutorial.python.org',
            'tag_ids': [(6, 0, [tag.id])],
            'user_id': self.test_user.id
        })

        # Recompute count
        tag._compute_bookmark_count()
        self.assertEqual(tag.bookmark_count, 2)

    def test_tag_required_fields(self):
        """Test required field validation for tags"""
        # Test missing name
        with self.assertRaises(Exception):
            self.env['odoo.bookmark.tag'].create({
                'user_id': self.test_user.id
            })

        # Test missing user_id
        with self.assertRaises(Exception):
            self.env['odoo.bookmark.tag'].create({
                'name': 'python'
            })


@tagged('standard', 'at_install')
class TestBookmarkIntegration(TransactionCase):
    """Integration tests for bookmark and tag models"""

    def setUp(self):
        super().setUp()
        self.test_user = self.env['res.users'].create({
            'name': 'Integration Test User',
            'login': 'integration_user',
            'email': 'integration@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

    def test_bookmark_tag_relationship(self):
        """Test Many2many relationship between bookmarks and tags"""
        # Create tags
        tag_python = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': self.test_user.id
        })
        tag_web = self.env['odoo.bookmark.tag'].create({
            'name': 'web',
            'user_id': self.test_user.id
        })

        # Create bookmark with tags
        bookmark = self.env['odoo.bookmark'].create({
            'name': 'Django Documentation',
            'url': 'https://docs.djangoproject.com',
            'tag_ids': [(6, 0, [tag_python.id, tag_web.id])],
            'user_id': self.test_user.id
        })

        # Test relationship from bookmark side
        self.assertEqual(len(bookmark.tag_ids), 2)
        self.assertIn(tag_python, bookmark.tag_ids)
        self.assertIn(tag_web, bookmark.tag_ids)

        # Test relationship from tag side (via search)
        python_bookmarks = self.env['odoo.bookmark'].search([
            ('tag_ids', 'in', tag_python.id)
        ])
        self.assertIn(bookmark, python_bookmarks)

    def test_user_data_isolation(self):
        """Test that users only see their own bookmarks and tags"""
        user2 = self.env['res.users'].create({
            'name': 'User 2',
            'login': 'user2',
            'email': 'user2@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

        # Create bookmark for user 1
        bookmark1 = self.env['odoo.bookmark'].create({
            'name': 'User 1 Bookmark',
            'url': 'https://user1.com',
            'user_id': self.test_user.id
        })

        # Create bookmark for user 2
        bookmark2 = self.env['odoo.bookmark'].create({
            'name': 'User 2 Bookmark',
            'url': 'https://user2.com',
            'user_id': user2.id
        })

        # Test that searches respect user ownership
        user1_bookmarks = self.env['odoo.bookmark'].search([
            ('user_id', '=', self.test_user.id)
        ])
        user2_bookmarks = self.env['odoo.bookmark'].search([
            ('user_id', '=', user2.id)
        ])

        self.assertIn(bookmark1, user1_bookmarks)
        self.assertNotIn(bookmark2, user1_bookmarks)
        self.assertIn(bookmark2, user2_bookmarks)
        self.assertNotIn(bookmark1, user2_bookmarks)

    def test_public_bookmark_visibility(self):
        """Test public bookmark visibility logic"""
        # Create private bookmark
        private_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Private Bookmark',
            'url': 'https://private.com',
            'is_public': False,
            'user_id': self.test_user.id
        })

        # Create public bookmark
        public_bookmark = self.env['odoo.bookmark'].create({
            'name': 'Public Bookmark',
            'url': 'https://public.com',
            'is_public': True,
            'user_id': self.test_user.id
        })

        # Test public bookmarks search
        public_bookmarks = self.env['odoo.bookmark'].search([
            ('is_public', '=', True)
        ])

        self.assertIn(public_bookmark, public_bookmarks)
        self.assertNotIn(private_bookmark, public_bookmarks)
