# -*- encoding: utf-8 -*-
import netsvc
from osv import fields, osv
import pooler
from tools.translate import _
import time
from datetime import date, datetime


class hr_payroll_ma(osv.osv):

    def _get_journal(self, cr, uid, context):
        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('name', '=', 'journal des salaires')], limit=1)
        if res:
            return res[0]
        else:
            return False

    def _get_currency(self, cr, uid, context):
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        res = currency_obj.search(cr, uid, [('symbol', '=', 'MAD')], limit=1)
        if res:
            return res[0]
        else:
            return False

    def _get_partner(self, cr, uid, data, context={}):
        company_obj = pooler.get_pool(cr.dbname).get('res.company')
        ids_company=company_obj.search(cr,uid,[])
        res=company_obj.read(cr,uid,ids_company[0])
        if res:
            return res['partner_id'][0]
        else:
            return False
        
    def _total_net(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for payroll in self.browse(cr, uid, ids, context):
            net=0
            for line in payroll.bulletin_line_ids:
                net+=line.salaire_net_a_payer
            result[payroll.id] = net
        return result
    
    _name = "hr.payroll_ma"
    _description = 'Saisie des bulletins'
    _order = "number"
    _columns = {
        'name': fields.char('Description', size=64),
        'number': fields.char('Numero du salaire', size=32, readonly=True),
        'date_salary': fields.date('Date salaire', states={'open':[('readonly', True)], 'close':[('readonly', True)]}, select=1),
        'partner_id': fields.many2one('res.partner', 'Employeur', change_default=True, readonly=True, required=True, states={'draft':[('readonly', False)]}, select=1),
        'period_id': fields.many2one('account.period', 'Periode', domain=[('state', '<>', 'done')], readonly=True, required=True, states={'draft':[('readonly', False)]}, select=1),
        'bulletin_line_ids': fields.one2many('hr.payroll_ma.bulletin', 'id_payroll_ma', 'Bulletins', readonly=True, states={'draft':[('readonly', False)]}),
        'move_id': fields.many2one('account.move', 'salary Movement', readonly=True, help="Link to the automatically generated account moves."),
        'currency_id': fields.many2one('res.currency', 'Devise', required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirme'),
            ('paid', 'Done'),
            ('cancelled', 'Cancelled')
        ], 'State', select=2, readonly=True),
        'total_net': fields.function(_total_net, method=True, type='float',digits=(16, 2), string='Total net'),
        }
    def _name_get_default(self, cr, uid, context=None):
            return self.pool.get('ir.sequence').get(cr, uid, 'hr.payroll_ma')
    _defaults = {
        'number': _name_get_default,
        'date_salary': lambda * a: time.strftime('%Y-%m-%d'),
        'state': lambda * a: 'draft',
        'journal_id': _get_journal,
        'partner_id': _get_partner,
        'currency_id': _get_currency,

    }
    def _check_unicite(self, cr, uid, ids):
           for unicite in self.browse(cr, uid, ids):
               unicite_id = self.search(cr, uid, [('period_id', '=', int(unicite.period_id)), ('partner_id', '=', int(unicite.partner_id)) ])
               if len(unicite_id) > 1:
                   return False
           return True

    _constraints = [
        (_check_unicite, u'Cette période éxiste déjà', ['period'])
        ]    
        
    def onchange_period_id(self, cr, uid, ids, period_id, partner_id):
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
        period = self.pool.get('account.period').browse(cr, uid, period_id)

        result = {'value': {
                            'name' :   'Salaires %s de la periode %s' % (partner.name, period.name),
                            }
                    }

        return result
    
    def draft_cb(self, cr, uid, ids, context=None):
        for sal in self.browse(cr, uid, ids):
            if sal.move_id:
                raise osv.except_osv(_('Error !'), _(u'Veuillez d\'abord supprimer les écritures comptables associés'))

        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def confirm_cb(self, cr, uid, ids, context=None):
        self.action_move_create(cr, uid, ids)
        return self.write(cr, uid, ids, {'state':'confirmed'}, context=context)

    def cancel_cb(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancelled'}, context=context)
    
    def generate_employees(self, cr, uid, ids, context={}):
        pool = pooler.get_pool(cr.dbname)
        employees = self.pool.get('hr.employee')
        obj_contract = self.pool.get('hr.contract')
        ids_employees = employees.search(cr, uid, [('active','=',True)])
        emp = employees.read(cr, uid, ids_employees,['id','name'])
        payroll_ma = pool.get('hr.payroll_ma').browse(cr, uid, ids[0])
        
        line={}
        if payroll_ma.state == 'draft':
            sql = '''
            DELETE from hr_payroll_ma_bulletin where id_payroll_ma = %s
                '''
            cr.execute(sql, (ids[0],))
        
        for e in emp :
            result = pool.get('hr.payroll_ma.bulletin').onchange_employee_id(cr, uid, ids, e['id'],payroll_ma.period_id.id)['value']
            employee = self.pool.get('hr.employee').browse(cr, uid, e['id'])
            contract_ids = obj_contract.search(cr, uid, [('employee_id','=',e['id']),], order='date_start', context=context)
            if contract_ids:
                con = contract_ids[-1:][0]
                contract=obj_contract.browse(cr, uid, con)
                line = {
                'employee_id' : e['id'],'employee_contract_id' : con,'working_days':result['working_days'],
                'normal_hours' : result['normal_hours'],'hour_base' : result['hour_base'],
                'salaire_base' : contract.wage,'id_payroll_ma':ids[0],'period_id':payroll_ma.period_id.id
                } 
                pool.get('hr.payroll_ma.bulletin').create(cr, uid, line)
                
        return True
    
    def compute_all_lines(self, cr, uid, ids, context={}):
        for sal in self.browse(cr, uid, ids):
            bulletins = self.pool.get('hr.payroll_ma.bulletin').search(cr, uid,[('id_payroll_ma','=',sal.id)])
            bulletins2 = self.pool.get('hr.payroll_ma.bulletin').browse(cr, uid, bulletins)
            for bul in bulletins2:
                bul.compute_all_lines()
        return True
    ##generation des ecriture comptable
    def action_move_create(self, cr, uid, ids):
        context = {}
        #pool = pooler.get_pool(cr.dbname)
        params = self.pool.get('hr.payroll_ma.parametres')
        ids_params = params.search(cr, uid, [])
        dictionnaire = params.read(cr, uid, ids_params[0])
        for sal in self.browse(cr, uid, ids):
            company_currency = sal.currency_id.id

            # one move line per salary period

            date = sal.date_salary or time.strftime('%Y-%m-%d')
            partner = sal.partner_id.id

            journal_id = sal.journal_id.id
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
            if journal.centralisation:
                raise osv.except_osv(_('UserError'),
                        _('Cannot create salary move on centralised journal'))

            period_id = sal.period_id and sal.period_id.id or False
            if not period_id:
                raise osv.except_osv(_('UserError'),
                        _('Periode obligaoire'))
            
            move = {}
            move_lines = []
            bulletins=self.pool.get('hr.payroll_ma.bulletin').search(cr, uid,[('id_payroll_ma','=',sal.id)])
            bulletins_query_cond=str(tuple(bulletins))
            if tuple(bulletins).__len__() == 1:
                #string = str(tuple(bulletins)).remove(',')
                bulletins_query_cond='('+str(bulletins[0])+')'


            sql='''
                SELECT l.name as name , sum(subtotal_employee) as subtotal_employee,sum(subtotal_employer) as           subtotal_employer,l.credit_account_id,l.debit_account_id
                FROM hr_payroll_ma_bulletin_line l
                LEFT JOIN account_account aa ON aa.id=l.credit_account_id
                RIGHT JOIN account_account ab ON ab.id=l.debit_account_id
                where l.type = 'cotisation' and id_bulletin in %s
                group by l.name,l.credit_account_id,l.debit_account_id  
                '''% (bulletins_query_cond)
            cr.execute(sql)
            data=cr.dictfetchall()
    #def action_move_create2(self, cr, uid, ids):
            for line in data :
                if line['subtotal_employee'] :
                        #=======================================================
                        # move_line_debit={
                        #             'account_id' : sal.employee_contract_id.salary_debit_account_id.id,
                        #             'period_id' : period_id,
                        #             'journal_id' : journal_id,
                        #             'date' : date,
                        #             'name' : (line.name or '\\' )+ ' Salarial',
                        #             'debit' : line.subtotal_employee,
                        #             'partner_id' : line.partner_id and line.partner_id.id,
                        #             'currency_id': company_currency,
                        #             }
                        #=======================================================
                    move_line_credit = {
                                     'account_id' : line['credit_account_id'],
                                     'period_id' : period_id,
                                     'journal_id' : journal_id,
                                     'date' : date,
                                     'name' : (line['name'] or '\\') + ' Salarial',
                                     'credit' : line['subtotal_employee'],
                                     'debit' : 0,
                                     'partner_id' : partner,
                                     'currency_id': company_currency,
                                     'state' : 'valid'
                                     }
                        #move_lines.append((0,0,move_line_debit))
                    move_lines.append((0, 0, move_line_credit)) 
                    
                if line['subtotal_employer'] :
                        move_line_debit = {
                                     'account_id' : line['debit_account_id'],
                                     'period_id' : period_id,
                                     'journal_id' : journal_id,
                                     'date' : date,
                                     'name' : (line['name'] or '\\') + ' Patronal',
                                     'debit' : line['subtotal_employer'],
                                     'credit' :0,
                                     'partner_id' : partner,
                                     'currency_id': company_currency,
                                     'state' : 'valid'
                                     }
                        move_line_credit = {
                                     'account_id' : line['credit_account_id'],
                                     'period_id' : period_id,
                                     'journal_id' : journal_id,
                                     'date' : date,
                                     'name' : (line['name'] or '\\') + ' Patronal',
                                     'debit' : 0,
                                     'credit' : line['subtotal_employer'],
                                     'partner_id' : partner,
                                     'currency_id': company_currency,
                                     'state' : 'valid'
                                     }
                        move_lines.append((0, 0, move_line_debit))
                        move_lines.append((0, 0, move_line_credit))
            sql='''
                SELECT sum(salaire_brute) as salaire_brute,sum(salaire_net_a_payer) as salaire_net_a_payer,sum(arrondi) as arrondi,sum(deduction) as deduction
                FROM hr_payroll_ma_bulletin b
                LEFT JOIN hr_payroll_ma pm ON pm.id=b.id_payroll_ma
                where b.id_payroll_ma = %s 
                '''% (sal.id)
            cr.execute(sql)
            data=cr.dictfetchall()
            data = data[0] 
            move_line_debit = {
                                     'account_id' : dictionnaire['salary_debit_account_id'][0],
                                     'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                     'period_id' : period_id,
                                     'journal_id' : journal_id,
                                     'date' : date,
                                     'name' : 'Salaire Brute',
                                     'debit' :  data['salaire_brute']-data['deduction'],
                                     'credit' : 0,
                                     'partner_id' : partner,
                                     'currency_id': company_currency,
                                     'state' : 'valid'
                                     }
            move_line_arrondi = {
                                     'account_id' : dictionnaire['salary_debit_account_id'][0],
                                     'analytic_account_id': dictionnaire['analytic_account_id'][0],
                                     'period_id' : period_id,
                                     'journal_id' : journal_id,
                                     'date' : date,
                                     'name' : 'Arrondi',
                                     'debit' :  data['arrondi'],
                                     'credit' : 0,
                                     'partner_id' : partner,
                                     'currency_id': company_currency,
                                     'state' : 'valid'
                                     }
            move_line_credit = {
                                     'account_id' : dictionnaire['salary_credit_account_id'][0],
                                     'period_id' : period_id,
                                     'journal_id' : journal_id,
                                     'date' : date,
                                     'name' : 'Salaire net a payer',
                                     'credit' : data['salaire_net_a_payer'],
                                     'debit' : 0,
                                     'partner_id' : partner,
                                     'currency_id': company_currency,
                                     'state' : 'valid'
                                     }
            move_lines.append((0, 0, move_line_debit))
            move_lines.append((0, 0, move_line_arrondi))
            move_lines.append((0, 0, move_line_credit))
                           
            move = {'ref': sal.number,
                  'period_id' : period_id,
                  'journal_id' : journal_id,
                  'date' : date,
                  'state' : 'draft',
                  'name' : sal.name or '\\',
                  'line_id' : move_lines}
            move_id = self.pool.get('account.move').create(cr, uid, move)
            self.pool.get('hr.payroll_ma').write(cr, uid, sal.id, {'move_id' : move_id})
            return True

hr_payroll_ma()

class hr_payroll_ma_bulletin(osv.osv):
    

    _name = "hr.payroll_ma.bulletin"
    _description = 'bulletin'
    _order = "name"
    _columns = {
        'name': fields.char('Numero du salaire', size=32, readonly=True),
        'date_salary': fields.date('Date salaire', states={'open':[('readonly', True)], 'close':[('readonly', True)]}, select=1),
        'employee_id': fields.many2one('hr.employee', 'Employe', change_default=True, readonly=True, required=True, states={'draft':[('readonly', False)]}, select=1),
        'period_id': fields.many2one('account.period', 'Periode', select=1),
        'salary_line_ids': fields.one2many('hr.payroll_ma.bulletin.line', 'id_bulletin', 'lignes de salaire', readonly=True, states={'draft':[('readonly', False)]}),
        'employee_contract_id' : fields.many2one('hr.contract', u'contrat de travail', required=True, states={'draft':[('readonly', False)]}),
        'id_payroll_ma': fields.many2one('hr.payroll_ma', 'Ref Salaire', ondelete='cascade', select=True),
        'salaire_base' : fields.float('Salaire de base'),
        'normal_hours' : fields.float('Heures travaillee durant le mois'),
        'hour_base' : fields.float('Salaire heure'),
        'comment': fields.text('Informations complementaires'),
        'salaire':fields.float('Salaire Base', readonly=True, digits=(16, 2)),
        'salaire_brute':fields.float('Salaire Brute', readonly=True, digits=(16, 2)),
        'salaire_brute_imposable':fields.float('Salaire brute imposable', readonly=True, digits=(16, 2)),
        'salaire_net':fields.float('Salaire Net', readonly=True, digits=(16, 2)),
        'salaire_net_a_payer':fields.float('Salaire Net a payer', readonly=True, digits=(16, 2)),
        'salaire_net_imposable':fields.float('Salaire Net Imposable', readonly=True, digits=(16, 2)),
        'cotisations_employee':fields.float('Cotisations Employe', readonly=True, digits=(16, 2)),
        'cotisations_employer':fields.float('Cotisations Employeur', readonly=True, digits=(16, 2)),
        'igr':fields.float('Impot sur le revenu', readonly=True, digits=(16, 2)),
        'prime':fields.float('Primes', readonly=True, digits=(16, 2)),
        'indemnite':fields.float('Indemnites', readonly=True, digits=(16, 2)),
        'avantage':fields.float('Avantages', readonly=True, digits=(16, 2)),
        'exoneration':fields.float('Exonerations', readonly=True, digits=(16, 2)),
        'deduction':fields.float('Deductions', readonly=True, digits=(16, 2)),
        'working_days' : fields.float('Jours travailles', size=64, digits=(16, 2)),
        'prime_anciennete' : fields.float('Prime anciennete', size=64, digits=(16, 2)),
        'frais_pro': fields.float('Frais professionnels', size=64, digits=(16, 2)),
        'personnes': fields.integer('Personnes'),
        'absence':fields.float('Absences', size=64, digits=(16, 2)),
        'arrondi':fields.float('Arrondi', size=64, digits=(16, 2)),
        'logement':fields.float('Logement', size=64, digits=(16, 2)),
        }
    
    def _name_get_default(self, cr, uid, context=None):
            return self.pool.get('ir.sequence').get(cr, uid, 'hr.payroll_ma.bulletin')
    _defaults = {
        'name': _name_get_default,

    }
    def _check_unicite(self, cr, uid, ids):
           for unicite in self.browse(cr, uid, ids):
               unicite_id = self.search(cr, uid, [('period_id', '=', int(unicite.period_id)), ('employee_id', '=', int(unicite.employee_id)) ])
               if len(unicite_id) > 1:
                   return False
           return True

    _constraints = [
        (_check_unicite, u'Un bulletin de paie est repété pour un même employé', ['period', 'employee'])
        ]
    def onchange_contract_id(self, cr, uid, ids, contract_id):
        salaire_base = 0
        normal_hours = 0
        hour_base = 0
        if contract_id:
            contract = self.pool.get('hr.contract').browse(cr, uid, contract_id)
            salaire_base = contract.wage
            hour_base = contract.hour_salary
            normal_hours = contract.monthly_hour_number

        result = {'value': {
                            'salaire_base' : salaire_base,
                            'hour_base' : hour_base,
                            'normal_hours' : normal_hours,
                        }
                    }
        return result
    
    def onchange_employee_id(self, cr, uid, ids, employee_id,period_id):
        if not employee_id :
            return {}
        pool = pooler.get_pool(cr.dbname)
        #id_payroll_ma = ids[0]
        #payroll_ma = pool.get('hr.payroll_ma').browse(cr, uid, id_payroll_ma)
        employee_contract_id = False
        partner_id = False
        date_begin = time.strftime('%Y-%m-%d'),
        salaire_base = 0
        normal_hours = 0
        hour_base = 0
        days=0
       
        if not period_id:
            raise osv.except_osv(_(u'Période non définie !'),_(u"Vous devez d\'abord spécifier une période !") )
        if period_id and employee_id :
            
            period = self.pool.get('account.period').browse(cr, uid, period_id)
            #self.write(cr, uid, [bulletin.id], {'period_id' : payroll_ma.id })
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            if not employee.contract_id:
                raise osv.except_osv(_(u'Pas de contrat !'),_(u"Vous devez d\'abord saisir un contrat pour cet employé !") )

            sql = '''select sum(number_of_days) from hr_holidays h
                left join hr_holidays_status s on (h.holiday_status_id=s.id)
                where date_from >= '%s' and date_to <= '%s' 
                and employee_id = %s 
                and state = 'validate' 
                and s.payed=False''' % (period.date_start, period.date_stop, employee_id)
            cr.execute(sql)
            res = cr.fetchone()
            if res[0] == None:
                days = 0
            else :
                days = res[0]
             
            #for contract in employee.contract_ids :
            #    if date_begin and contract.date_start <= date_begin and \
            #    (contract.date_end and contract.date_end >= date_begin or not contract.date_end) :
            #        employee_contract_id = contract.id
            #        salaire_base = contract.wage
            #        hour_base = contract.hour_salary
            #        normal_hours = contract.monthly_hour_number
                    
            result = {'value': {
                            'employee_contract_id' : employee.contract_id.id,
                            'salaire_base' : employee.contract_id.wage,
                            'hour_base' : employee.contract_id.hour_salary,
                            'normal_hours' : employee.contract_id.monthly_hour_number,
                            'working_days' : 26 - abs(days),
                            'period_id' : period_id
                        }
                    }

            return result
    

    
    #La fonction pour le calcul du taux de la prime d'anciennete
    def get_prime_anciennete(self, cr, uid, ids):
        pool = pooler.get_pool(cr.dbname)
        id_bulletin = ids[0]
        bulletin = pool.get('hr.payroll_ma.bulletin').browse(cr, uid, id_bulletin)
        date_salary = time.strftime('%Y-%m-%d')
        date_embauche = bulletin.employee_id.date
        if bulletin.employee_id.anciennete:
            date_salary = date_salary.split('-')
            date_embauche = date_embauche.split('-')
            jours1 = 0
            jours2 = 0
            jours1 = ((int(date_salary[0]) * 365) + (int(date_salary[1]) * 30) + int((date_salary[2])))
            jours2 = ((int(date_embauche[0]) * 365) + (int(date_embauche[1]) * 30) + (int(date_embauche[2])))
            anciennete = (jours1 - jours2) / 365
            objet_anciennete = self.pool.get('hr.payroll_ma.anciennete')
            id_anciennete = objet_anciennete.search(cr, uid, [])
            liste = objet_anciennete.read(cr, uid, id_anciennete, ['debuttranche', 'fintranche', 'taux'])
            for tranche in liste:
                if(anciennete >= tranche['debuttranche']) and (anciennete < tranche['fintranche']):
                    taux = (tranche['taux'])

            return taux
        else:
            return 0.0
    ####La fonction pour la calcul de IGR
    def get_igr(self, cr, uid, ids, montant, cotisations):
        #print('fonction IGR')
        res = {}
        taux=0
        somme=0
        salaire_net_imposable = 0
        pool = pooler.get_pool(cr.dbname)
        id_bulletin = ids[0]
        bulletin = pool.get('hr.payroll_ma.bulletin').browse(cr, uid, id_bulletin)
        personnes = bulletin.employee_id.chargefam
        logement = bulletin.employee_id.logement
        params = self.pool.get('hr.payroll_ma.parametres')
        ids_params = params.search(cr, uid, [])
        dictionnaire = params.read(cr, uid, ids_params[0])
        fraispro = montant * dictionnaire['fraispro'] / 100
        if fraispro < dictionnaire['plafond']:
            salaire_net_imposable = montant - fraispro - cotisations - logement
        else :
            salaire_net_imposable = montant - dictionnaire['plafond'] - cotisations - logement
        
        objet_ir = self.pool.get('hr.payroll_ma.ir')
        id_ir = objet_ir.search(cr, uid, [])
        liste = objet_ir.read(cr, uid, id_ir, ['debuttranche', 'fintranche', 'taux', 'somme'])
        for tranche in liste:
            if(salaire_net_imposable >= tranche['debuttranche']/12) and (salaire_net_imposable < tranche['fintranche']/12):
                taux = (tranche['taux'])
                somme = (tranche['somme']/12) 
            
        ir_brute = (salaire_net_imposable * taux / 100) - somme
        if((ir_brute - (personnes * dictionnaire['charge'])) < 0):
            ir_net = 0
        else:
            ir_net = ir_brute - (personnes * dictionnaire['charge'])
        res = {'salaire_net_imposable':salaire_net_imposable,
             'taux':taux,
             'ir_net':ir_net,
             'credit_account_id':dictionnaire['credit_account_id'][0],
             'frais_pro' : fraispro,
             'personnes' : personnes
             }

        return res
    
    
    def compute_all_lines(self, cr, uid, ids, context={}):
        pool = pooler.get_pool(cr.dbname)
        params = self.pool.get('hr.payroll_ma.parametres')
        ids_params = params.search(cr, uid, [])
        dictionnaire = params.read(cr, uid, ids_params[0])
        id_bulletin = ids[0]
        bulletin = pool.get('hr.payroll_ma.bulletin').browse(cr, uid, id_bulletin)
        self.write(cr, uid, [bulletin.id], {'period_id' : bulletin.id_payroll_ma.period_id.id})
        sql = '''
        DELETE from hr_payroll_ma_bulletin_line where id_bulletin = %s
        '''
        cr.execute(sql, (id_bulletin,))
        salaire_base = bulletin.salaire_base
        normal_hours = bulletin.normal_hours
        hour_base = bulletin.hour_base
        working_days = bulletin.working_days
        
        salaire_brute = 0
        salaire_brute_imposable = 0
        salaire_net = 0
        salaire_net_imposable = 0
        cotisations_employee = 0
        cotisations_employer = 0 
        prime = 0
        indemnite = 0
        avantage = 0
        exoneration = 0
        prime_anciennete = 0
        deduction = 0
        logement = 0
        frais_pro = 0
        personne = 0
        absence = 0
        arrondi=0
        if salaire_base :
            absence += salaire_base - (salaire_base * (bulletin.working_days / 26))

            salaire_base_line = {
                'name' : 'Salaire de base', 'id_bulletin' : id_bulletin, 'type' : 'brute','base' : round(salaire_base,2), 
                'rate_employee' : round((bulletin.working_days / 26) * 100,2), 'subtotal_employee':round(salaire_base * (bulletin.working_days / 26),2),'deductible' : False,
               }
            salaire_brute += salaire_base * (bulletin.working_days / 26)
            
            pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, salaire_base_line)
        if normal_hours :
            normale_hours_line = {
                'name' : 'Heures normales', 'id_bulletin' : id_bulletin, 'type' : 'brute','base' : normal_hours, 
                'rate_employee' : hour_base, 'subtotal_employee':normal_hours * hour_base,'deductible' : False,
                }
            salaire_brute += hour_base * round(normal_hours)
            
            pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, normale_hours_line)

        salaire_brute_imposable = salaire_brute
        sql = '''
        SELECT l.montant,l.taux,r.name,r.categorie,r.type,r.formule,r.afficher,r.sequence,r.imposable,r.plafond,r.ir,r.anciennete,r.absence
        FROM hr_payroll_ma_ligne_rubrique l
        LEFT JOIN hr_payroll_ma_rubrique r on (l.rubrique_id=r.id)
        WHERE 
        (l.id_contract=%s and l.permanent=True) OR 
        (l.id_contract=%s and l.date_start <= %s and l.date_stop >= %s)
        order by r.sequence
        '''
        cr.execute(sql, (bulletin.employee_contract_id.id, bulletin.employee_contract_id.id, bulletin.period_id.date_start, bulletin.period_id.date_start))
        rubriques = cr.dictfetchall()
        ir = salaire_brute_imposable
        anciennete = 0
        for rubrique in rubriques :
            
            if(rubrique['categorie'] == 'majoration'):
                if rubrique['formule'] :
                    try:
                        rubrique['montant'] = eval(str(rubrique['formule']))
                    except Exception, e:
                        raise osv.except_osv(_('Formule Error !'), _('Formule Error : %s ' % (e)))

                taux = 1
                montant = rubrique['montant']
                if rubrique['taux']:
                    taux=rubrique['taux']
                    montant = rubrique['montant'] * taux
                if rubrique['absence']: 
                    taux = bulletin.working_days / 26
                    montant = rubrique['montant'] * taux
                    taux=taux * 100
                    absence += rubrique['montant'] - montant
                if rubrique['anciennete'] : anciennete += montant
                if rubrique['ir']:
                    if rubrique['plafond'] == 0:ir += montant
                    elif montant <= rubrique['plafond']:
                        ir += montant
                    elif montant > rubrique['plafond']:
                        ir += montant - rubrique['plafond']
                if not rubrique['imposable']:
                    if rubrique['plafond'] == 0:
                        exoneration += montant
                    elif montant <= rubrique['plafond']:
                        exoneration += montant
                    elif montant > rubrique['plafond']:
                        exoneration += rubrique['plafond']
                        salaire_brute_imposable += montant - rubrique['plafond']
                if rubrique['type'] == 'prime':
                        prime += montant
                elif rubrique['type'] == 'indemnite':
                        indemnite += montant
                elif rubrique['type'] == 'avantage':
                        avantage += montant
                
                majoration_line = {
                'name' : rubrique['name'], 'id_bulletin' : id_bulletin, 'type' : 'brute','base' : rubrique['montant'],
                 'rate_employee' : taux , 'subtotal_employee':montant, 'deductible' : False,'afficher' : rubrique['afficher']
                    }
                
                pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, majoration_line)
        taux_anciennete = self.get_prime_anciennete(cr, uid, ids) / 100
 
        prime_anciennete = (salaire_brute + anciennete) * taux_anciennete
        if taux_anciennete :
            anciennete_line = {
                'name' : 'Prime anciennete', 'id_bulletin' : id_bulletin,'type' : 'brute',
                'base' : (salaire_brute + anciennete), 'rate_employee' : taux_anciennete, 'subtotal_employee':prime_anciennete,
                'deductible' : False,
                }
            pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, anciennete_line)

        salaire_brute += prime + indemnite + avantage + prime_anciennete
        salaire_brute_imposable=salaire_brute-exoneration
        cotisations = bulletin.employee_contract_id.cotisation.cotisation_ids
        base=0
        if bulletin.employee_id.affilie:
            for cot in cotisations :
                if cot.plafonee and salaire_brute_imposable >= cot.plafond:
                    base=cot.plafond
                else : base=salaire_brute_imposable
                cotisation_line = {
                'name' : cot.name,'id_bulletin' : id_bulletin,'type' : 'cotisation','base' : base,
                'rate_employee' : cot.tauxsalarial,'rate_employer' : cot.tauxpatronal,
                'subtotal_employee':base*cot.tauxsalarial/100,
                'subtotal_employer':base*cot.tauxpatronal/100,
                'credit_account_id': cot.credit_account_id.id,
                'debit_account_id' : cot.debit_account_id.id,
                'deductible' : True,
                } 
                cotisations_employee+=base*cot['tauxsalarial']/100
                cotisations_employer+=base*cot['tauxpatronal']/100
                pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, cotisation_line)
                    
            ###############Import sur le revenu
        res = self.get_igr(cr, uid, ids, ir+prime_anciennete, cotisations_employee)
        ir_line = {
                'name' : 'Impot sur le revenu', 'id_bulletin' : id_bulletin,'type' : 'cotisation','base' : res['salaire_net_imposable'], 'rate_employee' : res['taux'],
                'subtotal_employee':res['ir_net'],'credit_account_id': res['credit_account_id'], 'debit_account_id' : res['credit_account_id'],'deductible' : True,
                }
        pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, ir_line)
        for rubrique in rubriques :
            if(rubrique['categorie'] == 'deduction'):
                    deduction += rubrique['montant']
                    deduction_line = {
                    'name' : rubrique['name'], 'id_bulletin' : id_bulletin, 'type' : 'retenu','base' : rubrique['montant'], 
                    'rate_employee' : 100, 'subtotal_employee':rubrique['montant'], 'deductible' : True,'afficher' : rubrique['afficher'],
                   }
                    pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, deduction_line)
        salaire_net = salaire_brute - res['ir_net'] - cotisations_employee
        salaire_net_a_payer = salaire_brute - deduction - res['ir_net'] - cotisations_employee
        arrondi=1-(round(salaire_net_a_payer,2)-int(salaire_net_a_payer))
        if  arrondi !=1:
            arrondi=1-(salaire_net_a_payer-int(salaire_net_a_payer))
            salaire_net_a_payer+=arrondi
            arrondi_line= {
                        'name' : 'Arrondi', 'id_bulletin' : id_bulletin, 'type' : 'retenu','base' : arrondi, 
                        'rate_employee' : 100, 'subtotal_employee':arrondi, 'deductible' : True,
                       }
            
            pool.get('hr.payroll_ma.bulletin.line').create(cr, uid, arrondi_line)
        else :arrondi =0
        self.write(cr, uid, [bulletin.id], {   'salaire_brute' : salaire_brute,
                                               'salaire_brute_imposable':salaire_brute_imposable,
                                               'salaire_net':salaire_net,
                                               'salaire_net_a_payer':salaire_net_a_payer,
                                               'salaire_net_imposable':res['salaire_net_imposable'],
                                               'cotisations_employee':cotisations_employee,
                                               'cotisations_employer':cotisations_employer,
                                               'igr':res['ir_net'],
                                               'prime':prime,
                                               'indemnite':indemnite,
                                               'avantage':avantage,
                                               'deduction':deduction,
                                               'prime_anciennete':prime_anciennete,
                                               'exoneration':exoneration,
                                               'absence':absence,
                                               'frais_pro':res['frais_pro'],
                                               'personnes':res['personnes'],
                                               'arrondi' : arrondi,
                                               'logement' : bulletin.employee_id.logement
                                                })       

        
        return True
    

    
hr_payroll_ma_bulletin()


class hr_rubrique(osv.osv):
    _name = "hr.payroll_ma.rubrique"
    _description = "rubrique"
    _columns = {
        'name' : fields.char('Nom de la rubrique', size=64, required="True"),
        'code':fields.char('Code', size=64, required=False, readonly=False),
        'categorie' : fields.selection([('majoration', 'Majoration'),('deduction', 'Deduction'),
             ], 'Categorie'),
        'sequence': fields.integer('Sequence',help='Ordre d\'affichage dans le bulletin de paie'), 
        'type':fields.selection([
            ('prime', 'Prime'),('indemnite', 'Indemnite'),('avantage', 'Avantage'),
             ], 'Type'),
        'plafond':fields.float('Plafond exonere'),
        'formule':fields.char('Formule', size=64, required=False,help='''
        Pour les rubriques de type majoration on utilise les variables suivantes :
            salaire_base : Salaire de base
            hour_base : Salaire de l heure
            normal_hours : Les heures normales
            working_days : Jours travalles (imposable)
        '''),
        'imposable':fields.boolean('Imposable', required=False),
        'afficher':fields.boolean('Afficher', required=False,help='afficher cette rubrique sur le bulletin de paie'),
        'ir' :fields.boolean('IR', required=False),
        'anciennete' :fields.boolean('Anciennete', required=False),
        'absence' :fields.boolean('Absence', required=False),
        'note' : fields.text('Commentaire'),
                }
    _defaults = {
        'sequence': lambda * a: 1,
        'anciennete': lambda * a: True,
        'absence': lambda * a: True,
        'imposable': lambda * a: False,
        'afficher': lambda * a: True,
        'type': lambda * a: 'prime',
        'categorie': lambda * a: 'majoration',
        
    }
hr_rubrique()

class hr_ligne_rubrique(osv.osv):
    
    def _sel_rubrique(self, cr, uid, context=None):
        obj = self.pool.get('hr.payroll_ma.rubrique')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['name', 'id'], context)
        res = [(r['id'], r['name']) for r in res]
        return res
    _name = "hr.payroll_ma.ligne_rubrique"
    _description = "Ligne Rubrique"
    _columns = {
        'rubrique_id' : fields.many2one('hr.payroll_ma.rubrique', 'Rubrique', selection=_sel_rubrique),
        'id_contract': fields.many2one('hr.contract', 'Ref Contrat', ondelete='cascade', select=True),
        'montant' : fields.float('Montant'),
        'taux' : fields.float('Taux'), 
        'period_id': fields.many2one('account.period', 'Periode', domain=[('state', '<>', 'done')]),
        'permanent' : fields.boolean('Rubrique Permanante'),
        'date_start': fields.date('Date debut'),
        'date_stop': fields.date('Date fin'),
        'note' : fields.text('Commentaire'),
                }
    def _check_date(self, cr, uid, ids):
           for obj in self.browse(cr, uid, ids):
               if obj.date_start > obj.date_stop :
                   return False
           return True
    _order = 'date_start' 
    _constraints = [
        (_check_date, 'Date debut doit etre inferieur a date fin', ['date_stop'])
        ]
    
    def onchange_rubrique_id(self, cr, uid, ids, rubrique_id):
        rubrique = self.pool.get('hr.payroll_ma.rubrique').browse(cr, uid, rubrique_id)

        result = {'value': {
                            'montant' : rubrique.plafond,
                        }
                    }
        
        return result
    def onchange_period_id(self, cr, uid, ids, period_id=False):
        result={}
        if period_id :
            period = self.pool.get('account.period').browse(cr, uid, period_id)
            result = {'value': {
                            'date_start' :   period.date_start,
                            'date_stop' : period.date_stop
                            }
                    }

        return result
hr_ligne_rubrique()


class hr_payroll_ma_bulletin_line(osv.osv):
    
    #def _amount_employer(self, cr, uid, ids, prop, unknow_none,unknow_dict):
    #    res = {}
    #    for line in self.browse(cr, uid, ids):
    #        res[line.id] = round(float(line.base) * float(line.rate_employer),2)
    #    return res
    
    #def _amount_employee(self, cr, uid, ids, prop, unknow_none,unknow_dict):
    #    res = {}
    #    for line in self.browse(cr, uid, ids):
    #        res[line.id] = round(float(line.base) * float(line.rate_employee),2)
    #    return res


    _name = "hr.payroll_ma.bulletin.line"
    _description = "ligne de salaire"
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'id_bulletin': fields.many2one('hr.payroll_ma.bulletin', 'Ref Salaire', ondelete='cascade', select=True),
        'type' : fields.selection([('other', 'Autre'), ('retenu', 'Retenu'), ('cotisation', 'Cotisation'), ('brute', 'Salaire brute')], 'Type'),
        'credit_account_id': fields.many2one('account.account', 'Credit account', domain=[('type', '<>', 'view'), ('type', '<>', 'closed')], help="The income or expense account related to the selected product."),
        'debit_account_id': fields.many2one('account.account', 'Debit account', domain=[('type', '<>', 'view'), ('type', '<>', 'closed')], help="The income or expense account related to the selected product."),
        'base': fields.float('Base', required=True, digits=(16, 2)),
        'subtotal_employee': fields.float('Montant Employe', digits=(16, 2)),
        'subtotal_employer': fields.float('Montant Employeur', digits=(16, 2)),
        'rate_employee' : fields.float('Taux Employe', digits=(16, 2)),
        'rate_employer' : fields.float('Taux Employeur', digits=(16, 2)),
        #'quantity': fields.float('Quantity', required=True),
        'note': fields.text('Notes'),
        'deductible' : fields.boolean('deductible'),
        'afficher' : fields.boolean('Afficher'),
    }
    _defaults = {
        'afficher': lambda *a: True,
        'deductible' : lambda * a: False,
    }
    

hr_payroll_ma_bulletin_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
