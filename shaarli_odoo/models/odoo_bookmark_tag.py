from odoo import models, fields, api

class BookmarkTag(models.Model):
    _name = 'odoo.bookmark.tag'
    _description = 'Bookmark Tag'

    name = fields.Char('Name', required=True, index=True)
    color = fields.Integer('Color Index')
    bookmark_count = fields.Integer('Bookmarks', compute='_compute_bookmark_count')

    user_id = fields.Many2one('res.users', string='Owner',
                              default=lambda self: self.env.user,
                              required=True, ondelete='cascade')

    _sql_constraints = [
        ('name_user_uniq', 'unique (name, user_id)', 'Tag name must be unique per user!')
    ]

    @api.depends('name')
    def _compute_bookmark_count(self):
        for tag in self:
            tag.bookmark_count = self.env['odoo.bookmark'].search_count([
                ('tag_ids', 'in', tag.id)
            ])