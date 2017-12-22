# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
import time

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    matricule_dw = fields.Char(u'Matricule DW')
    matricule_dw_bcp = fields.Char(u'Matricule DW BCP')
    ##### CHECK LIST ####
    ##### Documents Apportés ####
    has_cin = fields.Boolean(u'Check CIN', default=False)
    has_passport = fields.Boolean(u'Check Passport', default=False)
    has_carte_sejour = fields.Boolean(u'Check Carte Séjour', default=False)
    has_photos = fields.Boolean(u'Check Diplome', default=False)
    has_fiche_anthropometrique = fields.Boolean(u'Check Fiche Anthropométrique', default=False)
    has_radio_pulmonaire = fields.Boolean(u'Check Radio Pulmonaire', default=False)
    has_justif_salaire = fields.Boolean(u'Check Justif Salaire', default=False)
    has_attestation_travail = fields.Boolean(u'Check Attestation Travail', default=False)
    has_diplome = fields.Boolean(u'Check Diplome', default=False)

    date_depot_diplome =fields.Datetime('Date Depot CIN')
    date_depot_passport = fields.Datetime('Date Depot Carte Séjour')
    date_depot_photos = fields.Datetime('Date Depot Photos')
    date_depot_fiche_anthropometrique = fields.Datetime('Date Depot Fiche Anthropométrique')
    date_depot_radio_pulmonaire = fields.Datetime('Date Depot Radio Pulmonaire')
    date_depot_justif_salaire = fields.Datetime('Date Depot Justif Salaire')
    date_depot_cin = fields.Datetime('Date Depot Attestation Travail')


class EmployeeDWCategory(models.Model):

    _name = "hr.employee.dw.category"
    _description = "Employee DW Category"

    name = fields.Char(string="Categorie", required=True)
    salaire_base= fields.Float(u'Salaire de base')
    salaire_net = fields.Float(u'Salaire Net')
    indimnite_transport = fields.Float(u'Indimnité Transport')
    indimnite_panier = fields.Float(u'Indimnité Panier')




# class ResCity(models.Model):
#     _name = "res.city"
#
#     name = fields.Char('City')
#     district_id = fields.Many2one('res.country.state', u'District')

