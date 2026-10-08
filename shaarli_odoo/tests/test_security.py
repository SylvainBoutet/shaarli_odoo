# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestBookmarkSecurity(TransactionCase):
    """Access rights of the bookmark groups"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bookmark_user = new_test_user(
            cls.env,
            login='bookmark_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.bookmark_manager = new_test_user(
            cls.env,
            login='bookmark_manager',
            groups='base.group_user,shaarli_odoo.group_bookmark_manager',
        )
        cls.basic_user = new_test_user(
            cls.env,
            login='basic_user',
            groups='base.group_user',
        )
        cls.public_user = cls.env.ref('base.public_user')
        cls.public_bookmark = cls.env['odoo.bookmark'].create({
            'name': 'Public Bookmark',
            'url': 'https://public-test.com',
            'is_public': True,
            'user_id': cls.bookmark_user.id,
        })

    def test_bookmark_user_can_crud_own_bookmarks(self):
        """A bookmark user creates, updates and deletes bookmarks"""
        bookmark = self.env['odoo.bookmark'].with_user(self.bookmark_user).create({
            'name': 'User Own Bookmark',
            'url': 'https://user-test.com',
        })
        self.assertEqual(bookmark.user_id, self.bookmark_user)
        bookmark.write({'name': 'Updated Bookmark'})
        self.assertEqual(bookmark.name, 'Updated Bookmark')
        bookmark.unlink()
        self.assertFalse(bookmark.exists())

    def test_bookmark_manager_can_crud_bookmarks(self):
        """A bookmark manager creates, updates and deletes bookmarks"""
        bookmark = self.env['odoo.bookmark'].with_user(self.bookmark_manager).create({
            'name': 'Manager Bookmark',
            'url': 'https://manager-test.com',
        })
        bookmark.write({'is_public': True})
        self.assertTrue(bookmark.is_public)
        bookmark.unlink()
        self.assertFalse(bookmark.exists())

    def test_manager_implies_user_group(self):
        """The manager group implies the user group"""
        self.assertTrue(self.bookmark_manager.has_group('shaarli_odoo.group_bookmark_user'))

    def test_public_user_can_read_public_bookmarks(self):
        """The public user reads public bookmarks"""
        bookmarks = self.env['odoo.bookmark'].with_user(self.public_user).search([
            ('id', '=', self.public_bookmark.id),
        ])
        self.assertEqual(bookmarks.name, 'Public Bookmark')

    def test_public_user_cannot_write_bookmarks(self):
        """The public user cannot modify a bookmark"""
        with self.assertRaises(AccessError):
            self.public_bookmark.with_user(self.public_user).write({'name': 'Hacked Bookmark'})

    def test_public_user_cannot_create_bookmarks(self):
        """The public user cannot create a bookmark"""
        with self.assertRaises(AccessError):
            self.env['odoo.bookmark'].with_user(self.public_user).create({
                'name': 'Unauthorized Bookmark',
                'url': 'https://hack-test.com',
                'user_id': self.public_user.id,
            })

    def test_basic_user_no_bookmark_access(self):
        """An internal user without bookmark group has no access"""
        with self.assertRaises(AccessError):
            self.env['odoo.bookmark'].with_user(self.basic_user).create({
                'name': 'Unauthorized Bookmark',
                'url': 'https://basic-test.com',
                'user_id': self.basic_user.id,
            })
        with self.assertRaises(AccessError):
            self.env['odoo.bookmark'].with_user(self.basic_user).search([])


@tagged('post_install', '-at_install')
class TestBookmarkTagSecurity(TransactionCase):
    """Access rights on tags"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bookmark_user = new_test_user(
            cls.env,
            login='tag_test_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.basic_user = new_test_user(
            cls.env,
            login='tag_basic_user',
            groups='base.group_user',
        )

    def test_user_can_crud_own_tags(self):
        """A bookmark user creates, updates and deletes tags"""
        tag = self.env['odoo.bookmark.tag'].with_user(self.bookmark_user).create({'name': 'python'})
        self.assertEqual(tag.user_id, self.bookmark_user)
        tag.write({'name': 'python-updated'})
        self.assertEqual(tag.name, 'python-updated')
        tag.unlink()
        self.assertFalse(tag.exists())

    def test_basic_user_no_tag_access(self):
        """An internal user without bookmark group cannot create tags"""
        with self.assertRaises(AccessError):
            self.env['odoo.bookmark.tag'].with_user(self.basic_user).create({'name': 'python'})
