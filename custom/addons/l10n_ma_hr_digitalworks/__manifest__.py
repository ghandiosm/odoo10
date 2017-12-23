# -*- coding: utf-8 -*-
# module template
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'HR DigitalWorks',
    'version': '10.0',
    'category': 'HR',
    'license': 'AGPL-3',
    'author': "Ghandi Mouad",
    'website': '',
    'depends': ['hr_payroll','l10n_ma_hr_payroll_10Basic'],
    'images': ['images/digital_works_logo.png'],
    'data': [
             'views/hr_view.xml',
             'views/l10n_ma_hr_digitalworks_view.xml'
             ],
    'installable': True,
    'application': True,
}
