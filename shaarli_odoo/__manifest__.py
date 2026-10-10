{
    'name': 'Shared Bookmarks',
    'version': '20.0.2.0.3',
    'category': 'Website',
    'summary': (
        'Save, tag and share web bookmarks in Odoo, publish the public ones '
        'on a website page and archive page content to read it later.'
    ),
    'description': (
        'Bookmarks with tags, notes and an owner, private or public. Public '
        'bookmarks are listed on the website, and the content of a page can '
        'be archived on its bookmark.'
    ),
    'author': 'Chti-tech | Sylvain Boutet',
    'website': 'https://github.com/SylvainBoutet/shaarli_odoo.git',
    'depends': ['base', 'web', 'mail', 'website'],
    'external_dependencies': {
        'python': ['requests', 'Pillow'],
    },
    'data': [
        # SECURITY
        'security/security.xml',
        'security/ir.access.csv',

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
    "images": [
        'static/description/banner.png',
        'static/description/main_screenshot.png',
    ],
}
