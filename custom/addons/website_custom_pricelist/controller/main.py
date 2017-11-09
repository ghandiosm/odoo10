from openerp.addons.website_sale.controllers import main
from openerp.http import request
from openerp import SUPERUSER_ID

def get_custom_pricelist():
    cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    sale_order = context.get('sale_order')
    if sale_order:
        pricelist = sale_order.pricelist_id
    else:
        website_ids = pool['website'].search(cr, uid, [], context=context)
        if website_ids:
            website_data = pool('website').browse(cr, uid, website_ids[0], context=context)
            price_list = website_data.pricelist_id
            if price_list:
                return price_list
        partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        pricelist = partner.property_product_pricelist
    return pricelist

main.get_pricelist = get_custom_pricelist
    

    

     



     
