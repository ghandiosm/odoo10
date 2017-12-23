# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing det


from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
from odoo.exceptions import UserError
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    salaire_base = fields.Float(u'Salaire Base')
    indimnite_panier = fields.Float(u'Indimnité Panier')
    indimnite_transport = fields.Float(u'Indimnité Transport')
    grade_id = fields.Many2one('hr.employee.dw.grade', string="Employé Grade")
    category_id = fields.Many2one('hr.employee.dw.category', string="Employé Categorie")

    @api.onchange('grade_id')
    def _onchange_grade_id(self):
        """ This function sets partner email address based on partner
        """
        self.wage = self.grade_id.salaire_net
        self.salaire_base = self.grade_id.salaire_base
        self.indimnite_panier = self.grade_id.indimnite_panier
        self.indimnite_transport = self.grade_id.indimnite_transport

    @api.onchange('category_id','type_id','trial_date_start')
    def _onchange_category_id(self):
        """ This function sets partner email address based on partner
        """
        if self.trial_date_start:
            if (self.type_id.name == "CDI" and self.category_id.name=="Employee"):
                self.trial_date_end = (datetime.strptime(self.trial_date_start,'%Y-%m-%d') + relativedelta(months=6)).strftime('%Y-%m-%d')
            elif (self.type_id.name == "CDI" and self.category_id.name=="Cadre"):
                self.trial_date_end = (datetime.strptime(self.trial_date_start,'%Y-%m-%d') + relativedelta(months=3)).strftime('%Y-%m-%d')

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'

    indimnite_pro = fields.Float(u'Heures Production',compute='_compute_indimnite_pro')
    indimnite_pro_tx_normal = fields.Float(compute='_compute_indimnite_pro_tx_normal',
                                           string=u'Heures Production (Taux Normal)')
    indimnite_formation = fields.Float(u'Heures Formation')
    indimnite_conge = fields.Float(u'Heures Conge')
    bonus = fields.Float('Bonus')

    base_calcul_pack = fields.Float(compute='_compute_base_calcul_pack', string=u'Base Pack HS')
    pack_taux = fields.Float(compute='_compute_pack_taux', string=u'Taux Pack HS')

    base_calcul_challenge = fields.Float(compute='_compute_base_calcul_challenge', string=u'Base Challenge')
    challenge = fields.Float(compute='_compute_challenge', string=u'Challenge')

    retenu_sur_salaire = fields.Float(u'Retenu sur Salaire')
    reguls = fields.Float(u'Réguls')

    @api.one
    def _compute_indimnite_pro(self):
        timesheets_cms_object = self.env['hr.timesheet.cms']
        timesheets_cms_hours = timesheets_cms_object.search([('employee_id', '=', self.employee_id.id),
                                                                ('date', '>=', self.date_from),
                                                                ('date', '<=', self.date_to) ])
        total_hours = 0.0
        name = ""
        for timesheet_cms_hours in timesheets_cms_hours:
            nname = timesheet_cms_hours.temps_paie_cms
            print "Employee Name is  "+nname
            total_hours += timesheet_cms_hours.temps_paie_cms

        self.indimnite_pro = total_hours

    @api.one
    @api.depends('indimnite_pro')
    def _compute_indimnite_pro_tx_normal(self):
        for record in self:
            if (record.indimnite_pro <= 191):
                self.indimnite_pro_tx_normal = self.indimnite_pro
            if (record.indimnite_pro > 191):
                self.indimnite_pro_tx_normal = 191

    @api.one
    @api.depends('indimnite_pro', 'indimnite_conge')
    def _compute_base_calcul_pack(self):
        """ This function sets partner email address based on partner
        """
        for record in self:
            if (record.indimnite_pro + record.indimnite_conge - 191 >= 0):
                record.base_calcul_pack = record.indimnite_pro + record.indimnite_conge - 191
            else:
                record.base_calcul_pack = 0

    @api.one
    @api.depends('indimnite_pro', 'indimnite_conge')
    def _compute_base_calcul_pack(self):
        """ This function sets partner email address based on partner
        """
        for record in self:
            if (record.indimnite_pro + record.indimnite_conge - 191 >= 0):
                record.base_calcul_pack = record.indimnite_pro + record.indimnite_conge - 191
            else:
                record.base_calcul_pack = 0

    @api.one
    @api.depends('base_calcul_pack')
    def _compute_pack_taux(self):
        for record in self:
            if (record.base_calcul_pack <= 0):
                record.pack_taux = 0
            elif (record.base_calcul_pack <= 10 and record.base_calcul_pack > 0):
                record.pack_taux = 1.25
            elif (record.base_calcul_pack <= 20 and record.base_calcul_pack > 10):
                record.pack_taux = 1.5
            elif (record.base_calcul_pack <= 30 and record.base_calcul_pack > 20):
                record.pack_taux = 1.75
            elif (record.base_calcul_pack > 30):
                record.pack_taux = 2.0

    @api.one
    @api.depends('indimnite_pro', 'indimnite_conge')
    def _compute_base_calcul_challenge(self):
        for record in self:
            record.base_calcul_challenge = record.indimnite_pro + record.indimnite_conge

    @api.one
    @api.depends('base_calcul_challenge')
    def _compute_challenge(self):
        if (self.base_calcul_challenge <= 191):
            self.challenge = 0.0
        elif (self.base_calcul_challenge > 191):
            self.challenge = 500


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    matricule_dw = fields.Char(u'Matricule DW',copy=False)
    matricule_dw_bcp = fields.Char(u'Matricule DW BCP',copy=False)
    id_avaya = fields.Char(u'ID Avaya')
    adresse_personnelle = fields.Char(string="Adresse Personnelle", required=False)
    ville_personnelle = fields.Char(string="Ville", required=False)
    num_carte_sejour = fields.Char(u'N° Carte Séjour')
    date_expiration_cin = fields.Datetime('Date Expiration CIN')
    date_expiration_passport = fields.Datetime('Date Expiration Passport')
    date_expiration_carte_sejour = fields.Datetime('Date Expiration Carte Sejour')

    ##### CHECK LIST ####
    ##### Documents Apportés ####
    #####  => Employé ####

    has_cin = fields.Boolean(u'Check CIN', default=False)
    has_carte_sejour = fields.Boolean(u'Check Carte Séjour', default=False)
    has_photos = fields.Boolean(u'Check Diplome', default=False)
    has_fiche_anthropometrique = fields.Boolean(u'Check Fiche Anthropométrique', default=False)
    has_radio_pulmonaire = fields.Boolean(u'Check Radio Pulmonaire', default=False)
    has_justif_salaire = fields.Boolean(u'Check Justif Salaire', default=False)
    has_attestation_travail = fields.Boolean(u'Check Attestation Travail', default=False)
    has_diplome = fields.Boolean(u'Check Diplome(s)', default=False)

    date_depot_cin = fields.Datetime('Date Depot CIN')
    date_depot_photos = fields.Datetime('Date Depot Photos')
    date_depot_fiche_anthropometrique = fields.Datetime('Date Depot Fiche Anthropométrique')
    date_depot_radio_pulmonaire = fields.Datetime('Date Depot Radio Pulmonaire')
    date_depot_justif_salaire = fields.Datetime('Date Depot Justif Salaire')
    date_depot_attestation_travail = fields.Datetime('Date Depot Attestation Travail')
    date_depot_diplome = fields.Datetime('Date Depot Diplome(s)')

    #####  => Conjoint ####
    has_conjoint_actmariage = fields.Boolean(u'Check Acte Marriage', default=False)
    has_conjoint_cin = fields.Boolean(u'Check CIN', default=False)
    has_conjoint_attestation_travail = fields.Boolean(u'Check Attestation Travail', default=False)
    has_cojoint_cnss = fields.Boolean(u'Check CNSS', default=False)

    date_depot_conjoint_actmariage = fields.Datetime('Date Depot Acte Marriage')
    date_depot_conjoint_cin = fields.Datetime('Date Depot CIN')
    date_depot_conjoint_attestation_travail = fields.Datetime('Date Depot Attestation Travail')
    date_depot_cojoint_cnss = fields.Datetime('Date Depot CNSS')

    #####  => Enfants ####
    has_enfant_actnaissance = fields.Boolean(u'Check Acte Naissance', default=False)

    date_depot_enfant_actnaissance = fields.Datetime('Date Depot Acte Naissance')

    _sql_constraints = [
        ('matricule_dw', 'unique(matricule_dw)',
         'The Employee DW Matricule must be unique across the company(s).'),
        ('matricule_dw_bcp', 'unique(matricule_dw_bcp)',
         'The Employee DW BCP Matricule must be unique across the company(s).'),
        ('id_avaya', 'unique(id_avaya)',
         'The Employee ID Avaya must be unique across the company(s).')
    ]


class EmployeeDWGrde(models.Model):
    _name = "hr.employee.dw.grade"
    _description = "Employee DW Grade"

    name = fields.Char(string="Categorie", required=True)
    salaire_base = fields.Float(u'Salaire de base')
    salaire_net = fields.Float(u'Salaire Net')
    indimnite_transport = fields.Float(u'Indimnité Transport')
    indimnite_panier = fields.Float(u'Indimnité Panier')

class EmployeeDWCategory(models.Model):
    _name = "hr.employee.dw.category"
    _description = "Employee DW Category"

    name = fields.Char(string="Catégorie Employé", required=True)

class HrTimesheetCMS(models.Model):
    _name = "hr.timesheet.cms"
    _description = "HR Timesheet CMS"

    date = fields.Date('Date',required=True)
    employee_id = fields.Many2one('hr.employee', string=u'Employé', compute='_compute_employee')
    id_avaya = fields.Char(u'ID Avaya')
    matricule_dw = fields.Char(u'Matricule DW')
    matricule_dw_prod = fields.Char(u'Matricule DW Prod')
    appels_repondu = fields.Integer(u'Appels Répondus')
    appels_sortant = fields.Integer(u'Appels Sortants')
    temps_connecte = fields.Integer(u'Temps Connecté')
    temps_lunch = fields.Integer(u'Temps en Lunch')
    temps_paie_cms = fields.Float(u'Temps Paie CMS',compute ='_compute_temps_paie_cms')
    temps_paie_travaille = fields.Float(u'Temps Paie Pretendu',compute='_compute_temps_paie_trvaille')
    corrective_ids = fields.One2many('hr.timesheet.cms.corrective', 'timesheet_cms_id', string='Correctivess')

    @api.one
    @api.depends('temps_connecte','temps_lunch')
    def _compute_temps_paie_cms(self):
        # This will make sure we have on record, not multiple records.
        self.temps_paie_cms = (self.temps_connecte - self.temps_lunch)/3600

    @api.one
    @api.depends('id_avaya')
    def _compute_employee(self):
        # This will make sure we have on record, not multiple records.
        self.ensure_one()
        for record in self:
            if record.id_avaya:
                if not record.employee_id:
                    employees_object = self.env['hr.employee']
                    employees_avaya = employees_object.search([('id_avaya', '=', self.id_avaya)])
                    for employee_record in employees_avaya:
                        record.employee_id = employee_record.id
                        record.matricule_dw = employee_record.matricule_dw
                        record.matricule_dw_prod = employee_record.matricule_dw_bcp

    @api.one
    @api.depends('temps_paie_cms')
    def _compute_temps_paie_trvaille(self):
        total_hours_worked = 0.0
        for record in self:
            for line in record.corrective_ids:
                if line.type_operation == "add":
                    total_hours_worked += line.nbr_hours
                elif line.type_operation == "substracte":
                    total_hours_worked -= line.nbr_hours
            total_hours_worked+=record.temps_paie_cms
            record.temps_paie_travaille = total_hours_worked

class HrTimesheetCMSCorrective(models.Model):
    _name = "hr.timesheet.cms.corrective"
    _description = "HR Timesheet CMS Corrective"

    user_id = fields.Many2one("res.users", string='User', required=True)
    type_operation = fields.Selection([
        ('add', 'Ajouter'),
        ('substracte', 'Diminuer'),
    ], u"Type Opération")
    nbr_hours = fields.Float(u'Nbre Heures')
    date = fields.Datetime(u'Date Opération')
    timesheet_cms_id = fields.Many2one("hr.timesheet.cms", string='Feuille de Temps CMS', required=True)
    motif_id = fields.Many2one('cms.corrective.motif', string=u'Motif', required=True)

    @api.model
    def create(self, vals):
        line = super(HrTimesheetCMSCorrective, self).create(vals)
        line.user_id = self.env.uid
        line.date = fields.Datetime.now()
        return line

class CMSCorrectiveMotif(models.Model):
    _name = "cms.corrective.motif"
    _description = "CMS Corrective Motif"

    name = fields.Char('Name', required=True)
    description = fields.Char('Description')

