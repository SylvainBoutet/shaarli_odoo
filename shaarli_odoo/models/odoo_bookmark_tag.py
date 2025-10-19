from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BookmarkTag(models.Model):
    _name = 'odoo.bookmark.tag'
    _description = 'Bookmark Tag'

    name = fields.Char('Name', required=True, index=True)
    color = fields.Integer('Color Index')
    bookmark_count = fields.Integer('Bookmarks', compute='_compute_bookmark_count')

    user_id = fields.Many2one('res.users', string='Owner',
                              default=lambda self: self.env.user,
                              required=True, ondelete='cascade')

    # Note: SQL constraints removed in Odoo 19 - using Python constraints only

    @api.constrains('name', 'user_id')
    def _check_name_user_unique(self):
        """Ensure tag name uniqueness per user (Python constraint)"""
        for record in self:
            if record.name and record.user_id:
                existing = self.search([
                    ('name', '=', record.name),
                    ('user_id', '=', record.user_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Tag name must be unique per user!'))

    @api.depends('name')
    def _compute_bookmark_count(self):
        for tag in self:
            tag.bookmark_count = self.env['odoo.bookmark'].search_count([
                ('tag_ids', 'in', tag.id)
            ])
