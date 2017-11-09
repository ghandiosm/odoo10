from openerp import models,fields

class website(models.Model):
    _inherit = "website"

    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'
    
    pricelist_id = fields.Many2one('product.pricelist',related='website_id.pricelist_id',string="Pricelist")
