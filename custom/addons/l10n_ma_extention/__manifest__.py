# -*- coding: utf-8 -*-
# module template
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Partner District',
    'version': '10.0',
    'category': 'Tools',
    'license': 'AGPL-3',
    'author': "Odoo Tips",
    'website': 'http://www.gotodoo.com/',
    'depends': ['base', 'hr'
                ],

    'images': ['images/main_screenshot.png'],
    'data': [
             'views/hr_view.xml',
             ],
    'installable': True,
    'application': True,
}
