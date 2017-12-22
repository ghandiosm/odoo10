# -*- coding: utf-8 -*-
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class BirthDateAgeEmployee(models.Model):
    _inherit = "hr.employee"

    age = fields.Integer(string="Age")
    
    @api.onchange('birthday')
    def _onchange_birthday(self):
        """Updates age field when birth_date is changed"""
        if self.birthday:
            d1 = datetime.strptime(self.birthday, "%Y-%m-%d").date()
            d2 = date.today()
            self.age = relativedelta(d2, d1).years

    @api.model
    def update_ages(self):
        """Updates age field for all partners once a day"""
        for rec in self.search([]):
            if rec.birthday:
                d1 = datetime.strptime(rec.birthday, "%Y-%m-%d").date()
                d2 = date.today()
                rec.age = relativedelta(d2, d1).years