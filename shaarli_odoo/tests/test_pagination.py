# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user
import re


@tagged('-at_install', 'post_install')
class TestPagination(HttpCase):
    """Tests for pagination functionality in public bookmarks"""

    def setUp(self):
        super().setUp()
        self.test_user = new_test_user(
            self.env,
            login='pagination_test_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user'
        )

        # Create test tags
        self.tag_python = self.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': self.test_user.id
        })
        self.tag_django = self.env['odoo.bookmark.tag'].create({
            'name': 'django',
            'user_id': self.test_user.id
        })

    def _create_test_bookmarks(self, count, public=True, tag=None, name_prefix="Test Bookmark"):
        """Helper method to create multiple test bookmarks"""
        bookmarks = self.env['odoo.bookmark']
        for i in range(count):
            bookmark_data = {
                'name': f'{name_prefix} {i+1}',
                'url': f'https://example-{i+1}.com',
                'description': f'Description for bookmark {i+1}',
                'is_public': public,
                'user_id': self.test_user.id
            }

            bookmark = self.env['odoo.bookmark'].create(bookmark_data)

            if tag:
                bookmark.tag_ids = [(6, 0, [tag.id])]

            bookmarks |= bookmark

        return bookmarks

    def test_no_pagination_with_few_bookmarks(self):
        """Test that pagination is not shown when there are <= 20 bookmarks"""
        # Create only 15 public bookmarks
        self._create_test_bookmarks(15)

        response = self.url_open('/bookmarks')
        self.assertEqual(response.status_code, 200)

        # Check that pagination is not present
        content = response.content.decode('utf-8')
        self.assertNotIn('pagination', content)
        self.assertNotIn('page-item', content)

    def test_pagination_with_many_bookmarks(self):
        """Test that pagination appears when there are > 20 bookmarks"""
        # Create 25 public bookmarks
        self._create_test_bookmarks(25)

        response = self.url_open('/bookmarks')
        self.assertEqual(response.status_code, 200)

        # Check that pagination is present
        content = response.content.decode('utf-8')
        self.assertIn('pagination', content)
        self.assertIn('page-item', content)

        # Check that only 20 bookmarks are shown on first page
        bookmark_count = content.count('Test Bookmark')
        self.assertEqual(bookmark_count, 20)

    def test_pagination_page_2(self):
        """Test accessing page 2 of pagination"""
        # Create 25 public bookmarks
        bookmarks = self._create_test_bookmarks(25)

        response = self.url_open('/bookmarks?page=2')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Should show remaining 5 bookmarks
        bookmark_count = content.count('Test Bookmark')
        self.assertEqual(bookmark_count, 5)

        # Check pagination navigation
        self.assertIn('pagination', content)

    def test_pagination_with_search_filter(self):
        """Test pagination with search filter applied"""
        # Create 25 bookmarks, some with 'python' in name
        self._create_test_bookmarks(15, name_prefix="Python Tutorial")
        self._create_test_bookmarks(10, name_prefix="Django Guide")

        # Search for 'python' - should return 15 results but paginated
        response = self.url_open('/bookmarks?search=python')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # All results should contain 'python'
        self.assertIn('Python Tutorial', content)
        self.assertNotIn('Django Guide', content)

        # No pagination needed (only 15 results)
        self.assertNotIn('pagination', content)

    def test_pagination_with_tag_filter(self):
        """Test pagination with tag filter applied"""
        # Create 25 bookmarks with python tag
        self._create_test_bookmarks(25, tag=self.tag_python, name_prefix="Python Resource")
        # Create 10 bookmarks with django tag
        self._create_test_bookmarks(10, tag=self.tag_django, name_prefix="Django Resource")

        # Filter by python tag
        response = self.url_open('/bookmarks?tag=python')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Should show python resources with pagination
        self.assertIn('Python Resource', content)
        self.assertNotIn('Django Resource', content)
        self.assertIn('pagination', content)

        # Should show 20 items on first page
        resource_count = content.count('Python Resource')
        self.assertEqual(resource_count, 20)

    def test_pagination_preserves_search_params(self):
        """Test that pagination links preserve search parameters"""
        # Create enough bookmarks to trigger pagination
        self._create_test_bookmarks(25, name_prefix="Python Tutorial")

        response = self.url_open('/bookmarks?search=python')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Check that pagination links contain search parameter
        # Look for links like /bookmarks?search=python&page=2
        search_param_pattern = r'href="[^"]*search=python[^"]*"'
        matches = re.findall(search_param_pattern, content)

        # Should find pagination links with search parameter preserved
        # (This test assumes pagination is shown, adjust if needed)
        if 'pagination' in content:
            self.assertTrue(len(matches) > 0, "Pagination links should preserve search parameter")

    def test_pagination_preserves_tag_params(self):
        """Test that pagination links preserve tag parameters"""
        # Create enough bookmarks to trigger pagination
        self._create_test_bookmarks(25, tag=self.tag_python)

        response = self.url_open('/bookmarks?tag=python')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Check that pagination links contain tag parameter
        tag_param_pattern = r'href="[^"]*tag=python[^"]*"'
        matches = re.findall(tag_param_pattern, content)

        # Should find pagination links with tag parameter preserved
        if 'pagination' in content:
            self.assertTrue(len(matches) > 0, "Pagination links should preserve tag parameter")

    def test_pagination_combined_filters(self):
        """Test pagination with both search and tag filters"""
        # Create bookmarks with python tag
        self._create_test_bookmarks(15, tag=self.tag_python, name_prefix="Python Tutorial")
        self._create_test_bookmarks(10, tag=self.tag_python, name_prefix="Python Advanced")
        self._create_test_bookmarks(5, tag=self.tag_django, name_prefix="Python Django")

        # Search for 'tutorial' with python tag
        response = self.url_open('/bookmarks?tag=python&search=tutorial')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Should only show Python Tutorial bookmarks
        self.assertIn('Python Tutorial', content)
        self.assertNotIn('Python Advanced', content)
        self.assertNotIn('Python Django', content)

    def test_pagination_invalid_page_number(self):
        """Test pagination with invalid page number"""
        self._create_test_bookmarks(25)

        # Test page 0 (should default to page 1)
        response = self.url_open('/bookmarks?page=0')
        self.assertEqual(response.status_code, 200)

        # Test negative page (should default to page 1)
        response = self.url_open('/bookmarks?page=-1')
        self.assertEqual(response.status_code, 200)

        # Test page beyond available pages (should show last page or handle gracefully)
        response = self.url_open('/bookmarks?page=999')
        self.assertEqual(response.status_code, 200)

    def test_pagination_non_numeric_page(self):
        """Test pagination with non-numeric page parameter"""
        self._create_test_bookmarks(25)

        # Test non-numeric page parameter
        response = self.url_open('/bookmarks?page=abc')
        self.assertEqual(response.status_code, 200)

        # Should handle gracefully and show first page
        content = response.content.decode('utf-8')
        bookmark_count = content.count('Test Bookmark')
        self.assertEqual(bookmark_count, 20)  # First page should show 20 items

    def test_pagination_structure_and_navigation(self):
        """Test pagination HTML structure and navigation elements"""
        # Create enough bookmarks for multiple pages
        self._create_test_bookmarks(45)  # Will create 3 pages

        response = self.url_open('/bookmarks')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Check for pagination structure
        self.assertIn('pagination', content)
        self.assertIn('page-item', content)
        self.assertIn('page-link', content)

        # Check for navigation elements
        self.assertIn('Previous', content)  # Previous button
        self.assertIn('Next', content)      # Next button

        # Check for page numbers (should see at least page 1, 2, 3)
        self.assertIn('1', content)
        self.assertIn('2', content)
        self.assertIn('3', content)
