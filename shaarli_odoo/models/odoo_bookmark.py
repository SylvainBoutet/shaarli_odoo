from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from datetime import datetime

class Bookmark(models.Model):
    _name = 'odoo.bookmark'
    _description = 'Bookmark'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Title', required=True, index=True, tracking=True)
    url = fields.Char('URL', required=True, index=True, tracking=True)
    description = fields.Text('Description', tracking=True)
    notes = fields.Html('Notes', tracking=True)

    favicon = fields.Binary('Favicon', attachment=True)
    thumbnail = fields.Binary('Thumbnail', attachment=True)

    tag_ids = fields.Many2many('odoo.bookmark.tag', string='Tags')

    is_public = fields.Boolean('Public', default=False, 
                               help="If checked, this bookmark will be visible to everyone")

    user_id = fields.Many2one('res.users', string='Owner',
                              default=lambda self: self.env.user,
                              required=True, ondelete='cascade')

    click_count = fields.Integer('Clicks', default=0)
    last_clicked = fields.Datetime('Last Clicked')

    color = fields.Integer('Color Index')

    # Archiving fields
    archived_content = fields.Html('Archived Content')
    archived_date = fields.Datetime('Archive Date')
    has_archive = fields.Boolean('Has Archive', compute='_compute_has_archive', store=True)
    content_type = fields.Char('Content Type')

    # Smart features
    domain = fields.Char('Domain', compute='_compute_domain', store=True)

    @api.depends('url')
    def _compute_domain(self):
        for record in self:
            if record.url:
                domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', record.url)
                record.domain = domain_match.group(1) if domain_match else ''
            else:
                record.domain = ''

    @api.depends('archived_content')
    def _compute_has_archive(self):
        for record in self:
            record.has_archive = bool(record.archived_content)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Normalize URL (add https:// if missing)
            if vals.get('url') and not re.match(r'^https?://', vals['url']):
                vals['url'] = 'https://' + vals['url']
        return super(Bookmark, self).create(vals_list)

    def write(self, vals):
        # Normalize URL (add https:// if missing)
        if vals.get('url') and not re.match(r'^https?://', vals['url']):
            vals['url'] = 'https://' + vals['url']
        return super(Bookmark, self).write(vals)

    def action_open_url(self):
        self.ensure_one()
        self.click_count += 1
        self.last_clicked = fields.Datetime.now()
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }

    def action_archive_page(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/bookmarks/archive/{self.id}',
            'target': 'self',
        }

    def action_view_archive(self):
        self.ensure_one()
        return {
            'name': _('Archived Page'),
            'res_model': 'odoo.bookmark',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('shaarli_odoo.view_bookmark_archived_page_form').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_delete_archive(self):
        self.ensure_one()
        self.write({
            'archived_content': False,
            'archived_date': False,
            'content_type': False
        })
        return True
