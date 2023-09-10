from odoo import fields, models, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import pytz
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

UTC = pytz.utc
IST = pytz.timezone('Asia/Kolkata')


class SecondAdvance(models.Model):
    _inherit = 'second.advance'

    def pay_advance(self):
        self.state = 'paid'
        company_payment_id = self.env['account.account'].search(
            [('name', '=', 'Cash'), ('company_id', '=', self.env.user.company_id.id)]).id
        cash_id = self.env['account.journal'].search(
            [('name', '=', 'Cash'), ('company_id', '=', self.env.user.company_id.id)]).id

        journal_list_1 = []
        journal_line_two = (0, 0, {
            'account_id': company_payment_id,
            'name': 'Advance Payment For Vehicle Request' + self.vehicle_req.name + ' For Vehicle No(' + self.vehicle_id.license_plate + ')',
            'debit': self.amount,
        })
        journal_list_1.append(journal_line_two)
        journal_line_one = (0, 0, {
            'account_id': self.env['branch.account'].search(
                [('name', '=', self.env.user.branch_id.id)]).account_id.id,
            'name': 'Advance Payment For Vehicle Request ' + self.vehicle_req.name + ' For Vehicle No(' + self.vehicle_id.license_plate + ')',
            'credit': self.amount,
        })
        journal_list_1.append(journal_line_one)
        journal_id_1 = self.env['account.move'].create({
            'date': datetime.now().date(),
            'ref': 'Advance Payment For Vehicle Request ' + self.vehicle_req.name + ' For Vehicle No(' + self.vehicle_id.license_plate + ')',
            'journal_id': cash_id,
            'line_ids': journal_list_1,
        })
        self.advance_id = journal_id_1.id
        journal_id_1.action_post()


        self.cash_rec_id = self.env['cash.transfer.record.register'].create({
            'date': self.date,
            'name': 'Advance For Vehicle Request ' + self.vehicle_req.name + ' For Vehicle No(' + self.vehicle_id.license_plate + ')-' + self.driver.driver.name,
            'credit': self.amount,
            'branch_id': self.env.user.branch_id.id,
            'company_id': self.env.user.company_id.id,
            'status': 'open',
            'transactions': True,
            'transaction_type': 'advance',
        }).id
        self.compute_cash_balance(self.date, self.env.user.branch_id.id)

        new_trip_sheet = self.env['trip.sheet'].search(
            [('vehicle_req', '=', self.vehicle_req.id), ('vehicle_id', '=', self.vehicle_id.id)])
        if new_trip_sheet:
            # trip_sheet_new_line = []
            # betta = []
            if self.amount:
                self.trip_line_id = self.env['trip.sheet.lines'].create({
                    'name': new_trip_sheet.id,
                    'description': 'Advance Paid',
                    'given': self.amount,
                }).id
                if self.vehicle_id.company_type != 'external':
                    self.betta_line_id = self.env['betta.lines'].create({
                        'trip_id': new_trip_sheet.id,
                        'description': 'Advance Paid',
                        'advance': self.amount,
                    }).id

        if self.vehicle_id.company_type == 'external':
            outpass = self.env['generate.out.pass.request'].search([('vehicle_req', '=', self.vehicle_req.id)])
            if outpass:
                inv = outpass.vendor_bill_id
                if inv.amount_residual > 0:
                    if self.branch_id.status != 'draft':
                        outpaid = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                                    active_ids=inv.ids).create(
                            {'payment_date': self.date,
                             'journal_id': self.branch_id.journal_id.id,
                             'payment_method_id': 1,
                             'amount': self.amount,
                             })
                        payment = outpaid._create_payments()
                        self.payment_id = payment.id
                    else:
                        raise UserError("No Cash Account Found For this Branch")


            contract = self.env['pending.contracts'].search([('vehicle_req', '=', self.vehicle_req.id)])
            if contract:
                contract.cdac = contract.cdac + self.amount
                contract.balance = contract.balance - self.amount

