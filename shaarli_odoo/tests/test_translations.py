# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTranslations(TransactionCase):
    """French labels of the bookmark form"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env['ir.module.module']._load_module_terms(['shaarli_odoo'], ['fr_FR'], overwrite=True)

    def test_archive_page_button_is_an_action(self):
        """The Archive Page button reads as an action in French"""
        arch = self.env.ref('shaarli_odoo.view_bookmark_form').with_context(lang='fr_FR').arch_db
        self.assertIn('string="Archiver la page"', arch)
