{
    'name': 'Odoo Bookmarks',
    'version': '17.0.2.0.3',
    'category': 'Website',
    'summary': 'Save and share bookmarks within Odoo',
    'description': """
Odoo Bookmarks
==============
A Shaarli-like bookmarking system integrated with Odoo.
Features:

- Save bookmarks with description and notes
- Organize with tags
- Public/private sharing options
- Page archiving
- Full-text search
- Browser extension support
    """,
    'author': 'Chti-tech | Sylvain Boutet',
    'website': 'https://github.com/SylvainBoutet/shaarli_odoo.git',
    'depends': ['base', 'web', 'mail', 'website'],
    'external_dependencies': {
        'python': ['requests', 'Pillow'],
    },
    'data': [
        # SECURITY
        'security/security.xml',
        'security/ir.model.access.csv',

        # VIEWS
        'views/bookmark_views.xml',
        'views/tag_views.xml',
        'views/website_templates.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'shaarli_odoo/static/tests/tours/**/*',
        ],
    },
    'demo': [
        'demo/bookmark_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    "images": ["static/description/public_view.png"],
}
