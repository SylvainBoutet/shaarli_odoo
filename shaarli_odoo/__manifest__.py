{
    'name': 'Odoo Bookmarks',
    'version': '18.0.1.0.0',
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
    'website': 'https://www.chti-tech.eu',
    'depends': ['base', 'web', 'mail', 'website'],
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
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    "images": ["static/description/public_view.png"],
}