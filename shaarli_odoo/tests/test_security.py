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

    def _private_bookmark_of(self, user):
        return self.env['odoo.bookmark'].create({
            'name': 'Private Bookmark',
            'url': 'https://private-test.com',
            'is_public': False,
            'user_id': user.id,
        })

    def test_user_reads_own_and_public_bookmarks_only(self):
        """A user sees their bookmarks and the public ones, not others' private ones"""
        other_user = new_test_user(
            self.env, login='other_bookmark_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user')
        own_private = self._private_bookmark_of(self.bookmark_user)
        other_private = self._private_bookmark_of(other_user)
        other_public = self.env['odoo.bookmark'].create({
            'name': 'Other Public', 'url': 'https://other-public.com',
            'is_public': True, 'user_id': other_user.id,
        })
        visible = self.env['odoo.bookmark'].with_user(self.bookmark_user).search([
            ('id', 'in', (own_private | other_private | other_public).ids),
        ])
        self.assertEqual(visible, own_private | other_public)
        with self.assertRaises(AccessError):
            other_private.with_user(self.bookmark_user).read(['name'])

    def test_user_cannot_modify_others_bookmarks(self):
        """A public bookmark of another user is read-only"""
        other_user = new_test_user(
            self.env, login='other_bookmark_user2',
            groups='base.group_user,shaarli_odoo.group_bookmark_user')
        other_public = self.env['odoo.bookmark'].create({
            'name': 'Other Public', 'url': 'https://other-public.com',
            'is_public': True, 'user_id': other_user.id,
        })
        with self.assertRaises(AccessError):
            other_public.with_user(self.bookmark_user).write({'name': 'Changed'})
        with self.assertRaises(AccessError):
            other_public.with_user(self.bookmark_user).unlink()
        with self.assertRaises(AccessError):
            self.env['odoo.bookmark'].with_user(self.bookmark_user).create({
                'name': 'For someone else', 'url': 'https://x.com', 'user_id': other_user.id,
            })

    def test_manager_reads_and_modifies_all_bookmarks(self):
        """A manager sees and modifies the private bookmarks of others"""
        private = self._private_bookmark_of(self.bookmark_user)
        as_manager = private.with_user(self.bookmark_manager)
        self.assertEqual(as_manager.name, 'Private Bookmark')
        as_manager.write({'name': 'Changed by manager'})
        self.assertEqual(private.name, 'Changed by manager')
        as_manager.unlink()
        self.assertFalse(private.exists())

    def test_public_user_cannot_read_private_bookmarks(self):
        """The public user does not see private bookmarks"""
        private = self._private_bookmark_of(self.bookmark_user)
        found = self.env['odoo.bookmark'].with_user(self.public_user).search([('id', '=', private.id)])
        self.assertFalse(found)

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

    def test_user_reads_but_cannot_modify_others_tags(self):
        """Tags are readable by all bookmark users, modifiable by their owner"""
        other_user = new_test_user(
            self.env, login='other_tag_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user')
        other_tag = self.env['odoo.bookmark.tag'].create({'name': 'other', 'user_id': other_user.id})
        self.assertEqual(other_tag.with_user(self.bookmark_user).name, 'other')
        with self.assertRaises(AccessError):
            other_tag.with_user(self.bookmark_user).write({'name': 'changed'})
        with self.assertRaises(AccessError):
            other_tag.with_user(self.bookmark_user).unlink()

    def test_manager_modifies_others_tags(self):
        """A manager modifies the tags of others"""
        manager = new_test_user(
            self.env, login='tag_manager',
            groups='base.group_user,shaarli_odoo.group_bookmark_manager')
        tag = self.env['odoo.bookmark.tag'].create({'name': 'mine', 'user_id': self.bookmark_user.id})
        tag.with_user(manager).write({'name': 'renamed'})
        self.assertEqual(tag.name, 'renamed')

    def test_basic_user_no_tag_access(self):
        """An internal user without bookmark group cannot create tags"""
        with self.assertRaises(AccessError):
            self.env['odoo.bookmark.tag'].with_user(self.basic_user).create({'name': 'python'})
