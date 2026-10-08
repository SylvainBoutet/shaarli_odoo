# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestPagination(HttpCase):
    """Tests for the pager of the public bookmarks page (20 per page)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Keep only the bookmarks of this test on the public page
        cls.env['odoo.bookmark'].search([('is_public', '=', True)]).write({'is_public': False})
        cls.test_user = new_test_user(
            cls.env,
            login='pagination_test_user',
            groups='base.group_user,shaarli_odoo.group_bookmark_user',
        )
        cls.tag_python = cls.env['odoo.bookmark.tag'].create({
            'name': 'python',
            'user_id': cls.test_user.id,
        })
        cls.tag_django = cls.env['odoo.bookmark.tag'].create({
            'name': 'django',
            'user_id': cls.test_user.id,
        })

    def _create_test_bookmarks(self, count, tag=None, name_prefix='Test Bookmark'):
        return self.env['odoo.bookmark'].create([{
            'name': f'{name_prefix} {i + 1}',
            'url': f'https://example-{i + 1}.com',
            'is_public': True,
            'user_id': self.test_user.id,
            'tag_ids': [(6, 0, tag.ids)] if tag else False,
        } for i in range(count)])

    def _get(self, url):
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')

    def test_no_pagination_with_few_bookmarks(self):
        """No pager under 20 bookmarks"""
        self._create_test_bookmarks(15)
        content = self._get('/bookmarks')
        self.assertEqual(content.count('Test Bookmark'), 15)
        self.assertNotIn('page-item', content)

    def test_pagination_with_many_bookmarks(self):
        """20 bookmarks on the first page, with a pager link to page 2"""
        self._create_test_bookmarks(25)
        content = self._get('/bookmarks')
        self.assertIn('page-item', content)
        self.assertIn('href="/bookmarks/page/2"', content)
        self.assertEqual(content.count('Test Bookmark'), 20)

    def test_pagination_page_2(self):
        """The pager link of page 2 shows the remaining bookmarks"""
        self._create_test_bookmarks(25)
        content = self._get('/bookmarks/page/2')
        self.assertEqual(content.count('Test Bookmark'), 5)
        self.assertIn('page-item', content)

    def test_pagination_page_query_parameter(self):
        """The page can also be given as a query parameter"""
        self._create_test_bookmarks(25)
        content = self._get('/bookmarks?page=2')
        self.assertEqual(content.count('Test Bookmark'), 5)

    def test_pagination_with_search_filter(self):
        """The search applies before the pager"""
        self._create_test_bookmarks(15, name_prefix='Python Tutorial')
        self._create_test_bookmarks(10, name_prefix='Django Guide')
        content = self._get('/bookmarks?search=python')
        self.assertEqual(content.count('Python Tutorial'), 15)
        self.assertNotIn('Django Guide', content)
        self.assertNotIn('page-item', content)

    def test_pagination_with_tag_filter(self):
        """The tag filter applies before the pager"""
        self._create_test_bookmarks(25, tag=self.tag_python, name_prefix='Python Resource')
        self._create_test_bookmarks(10, tag=self.tag_django, name_prefix='Django Resource')
        content = self._get('/bookmarks?tag=python')
        self.assertEqual(content.count('Python Resource'), 20)
        self.assertNotIn('Django Resource', content)
        self.assertIn('page-item', content)

    def test_pagination_preserves_search_params(self):
        """Pager links keep the search parameter"""
        self._create_test_bookmarks(25, name_prefix='Python Tutorial')
        content = self._get('/bookmarks?search=python')
        self.assertIn('href="/bookmarks/page/2?search=python"', content)

    def test_pagination_preserves_tag_params(self):
        """Pager links keep the tag parameter"""
        self._create_test_bookmarks(25, tag=self.tag_python)
        content = self._get('/bookmarks?tag=python')
        self.assertIn('href="/bookmarks/page/2?tag=python"', content)

    def test_pagination_combined_filters(self):
        """Search and tag filters combine"""
        self._create_test_bookmarks(15, tag=self.tag_python, name_prefix='Python Tutorial')
        self._create_test_bookmarks(10, tag=self.tag_python, name_prefix='Python Advanced')
        self._create_test_bookmarks(5, tag=self.tag_django, name_prefix='Python Django')
        content = self._get('/bookmarks?tag=python&search=tutorial')
        self.assertEqual(content.count('Python Tutorial'), 15)
        self.assertNotIn('Python Advanced', content)
        self.assertNotIn('Python Django', content)

    def test_pagination_out_of_range_page(self):
        """Out of range pages fall back on the first or last page"""
        self._create_test_bookmarks(25)
        self.assertEqual(self._get('/bookmarks?page=0').count('Test Bookmark'), 20)
        self.assertEqual(self._get('/bookmarks?page=-1').count('Test Bookmark'), 20)
        self.assertEqual(self._get('/bookmarks?page=999').count('Test Bookmark'), 5)

    def test_pagination_non_numeric_page(self):
        """A non-numeric page shows the first page"""
        self._create_test_bookmarks(25)
        self.assertEqual(self._get('/bookmarks?page=abc').count('Test Bookmark'), 20)

    def test_pagination_structure_and_navigation(self):
        """Three pages give links to pages 2 and 3"""
        self._create_test_bookmarks(45)
        content = self._get('/bookmarks')
        self.assertIn('page-link', content)
        self.assertIn('href="/bookmarks/page/2"', content)
        self.assertIn('href="/bookmarks/page/3"', content)
