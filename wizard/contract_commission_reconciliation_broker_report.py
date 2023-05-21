# -*- coding: utf-8 -*-

import datetime
import time

from odoo import api, models, fields


class WizardBrokerCommissionReport(models.TransientModel):
	_name = 'wizard.broker.commission.report'
	_description = 'Wizard Broker Commission Report'

	@api.onchange('type')
	def onchange_report_type(self):
		res = {'value': {}}
		if type != 'all':
			res['value'] = {'final_bool': False}
		return res

	date_from = fields.Date(
		"Start Date", required=True, default=time.strftime("%Y-01-01"))
	date_to = fields.Date(
		"End Date", required=True, default=time.strftime("%Y-%m-%d"))
	section_id = fields.Many2one('crm.team', 'Sales Team')

	# users_line = fields.One2many('res.users.contract.commission',
	#                              'broker_wizard_id', 'Users Line')
	type = fields.Selection(
		[('all', 'All'), ('selected', 'Selected')], 'Type', required=True, default='all')
	final_bool = fields.Boolean('Final', default=False)
	mpan_bool = fields.Boolean('MPAN/MPR', default=False)
	vatable = fields.Boolean(
		related='section_id.vatable',
		string="VatTable")

	user_tot_commission = fields.Float('User Tot Commission')
	user_average_tot = fields.Float('User Average Tot')
	user_total_uplift = fields.Float('User Total Uplift')
	user_total_usage = fields.Integer('User Total Usage')
	all_users_total_broker_commission = fields.Float('All User Total Broker Commission')
	all_paid_commission = fields.Float('All Paid Commission')
	all_users_vat_total = fields.Integer('All User vat Total')
	all_user_grand_total = fields.Float('All User Grand Total')
	total_commission_mac = fields.Float('Total Commission Mac')
	total_broker_commission_mac = fields.Float('Total Broker Commission Mac')

	def print_report(self):
		# data = self
		for rec in self:
			print ('--print datataa from ::>>>', rec.date_from)
			print ('--print datataa to ::>>>', rec.date_to)
			contract_ids = \
				self.env['res.contract'].sudo().search([(
					'user_id', '=', self.env.uid),
					('state', 'in', ('complete', 'livenocis_scanned', 'payment_confirm', 'query', 'admin_query')),
					('livenocis', '>=', rec.date_from), ('livenocis', '<=', rec.date_to)])
			print ('---print contract ids::>>>>>', contract_ids)

			return self.env.ref('dernetz.report_broker_commission_reconcile').report_action([])

	
	def get_counts(self, contract_ids):
		contract_count = 0
		mpan_count = 0
		res_contract_pool = self.env['res.contract']

		contract_count = len(contract_ids)
		if contract_ids:
			print ('--count contract ids :::>>>', contract_ids)
			for contract_obj in contract_ids:
				if contract_obj.meter_data_id:
					for meter in contract_obj.meter_data_id:
						if meter.mpan_code:
							mpan_count += 1
		return [{'contract': contract_count, 'meter': mpan_count}]

	
	def get_all_supplier_wise_data(self):
		self.get_data()
		self.all_supplier_list
		temp_all_supp = []
		cont_count = 1
		print ('--print self all supplier list ::>>>', self.all_supplier_list)
		for s_lst1 in self.all_supplier_list:
			for s_lst in s_lst1:
				if temp_all_supp and s_lst['supplier_id'] in [x['supplier_id'] for x in temp_all_supp]:
					print ('----print temp all supp :::>>>>', temp_all_supp)
					for s_l in temp_all_supp:
						print ('---supplier list ::>>>>>>>', s_lst['supplier_id'])
						if s_l['supplier_id'] == s_lst['supplier_id']:
							s_l['commission'] = (s_l['commission'] + (s_lst['supp_commission'])) or 0.00
							s_l['count_meter_no'] = s_l['count_meter_no'] and int(s_l['count_meter_no']) + \
																				s_lst['count_meter_supp']
							s_l['cont_no'] = s_l['cont_no'] and int(s_l['cont_no']) + s_lst['count_supp']
				else:
					manage_supp_dic = {
						'count_meter_no': s_lst['count_meter_supp'],
						'cont_no': s_lst['count_supp'],
						'supplier': s_lst['supplier_name'],
						'supplier_id': s_lst['supplier_id'],
						'commission': float(
							format(float(s_lst['supp_commission']), '.2f')) or 0.00,
					}
					temp_all_supp.append(manage_supp_dic)
				print ('----print temp all supp in ending of method:::>>>>', temp_all_supp)

		return temp_all_supp

	
	def get_all_supplier_wise_adj_data(self):
		self.all_supplier_adj_list
		temp_all_supp_adj = []

		cont_adj_count = 1
		if self.all_supplier_adj_list:
			print ('--print supplier all adj list ::>>>', self.all_supplier_adj_list)
			for sa_lst1 in self.all_supplier_adj_list:
				for sa_lst in sa_lst1:
					if temp_all_supp_adj and sa_lst['supplier_id'] in [x['supplier_id'] for x in temp_all_supp_adj]:
						print ('---print all temp supp adj :::>>>', temp_all_supp_adj)
						for s_l in temp_all_supp_adj:
							if s_l['supplier_id'] == sa_lst['supplier_id']:
								s_l['commission'] = (s_l['commission'] + (sa_lst['supp_commission'])) or 0.00
								s_l['cont_no'] = s_l['cont_no'] and int(s_l['cont_no']) + sa_lst['count_supp']
					else:
						manage_supp_adj_dic = {
							'cont_no': sa_lst['count_supp'],
							'supplier': sa_lst['supplier_name'],
							'supplier_id': sa_lst['supplier_id'],
							'commission': float(
								format(float(sa_lst['supp_commission']), '.2f')) or 0.00,
						}
						temp_all_supp_adj.append(manage_supp_adj_dic)
					print ('---print all temp supp adj in end of method:::>>>', temp_all_supp_adj)
		return temp_all_supp_adj

	
	def get_data(self):
		for rec in self:
			res_contract_pool = self.env['res.contract']
			section_pool = self.env['crm.team']
			broker_commission_pool = self.env['broker.commission.reconcile']
			meter_line_pool = self.env['meter.data.line']
			domain = []
			usr_lst = []
			section_obj = False
			print ('--print data section id :::>>>>>', rec.section_id)
			if rec.section_id:
				print ('--print data section id :::>>', rec.section_id)
				section_obj = rec.section_id
				print ('--print section obj ::>>>', section_obj)

			# if rec.type != 'all':
				# print '---print user line data ::>>>', data['users_line']
			# 	for con_user in rec.users_line:
			# 		usr_lst.append(con_user.user_id.id)
			# 	domain = [('id', 'in', usr_lst)]
			if section_obj and section_obj.external_broker:
				if section_obj.member_ids:
					print ('----section obj member ids :::>>>', section_obj.member_ids)
					for user in section_obj.member_ids:
						usr_lst.append(user.id)
					domain = [('id', 'in', usr_lst)]
				else:
					domain = [('id', 'in', [])]
			else:
				domain = [('id', 'in', [])]
			print ('---print domain ::>>>>', domain)
			user_ids = self.env['res.users'].search(domain)
			user_dic = {}
			user_list = []
			self.all_supplier_list = []
			self.all_supplier_adj_list = []
			self.manage_user_list = []
			if user_ids:
				print ('--printed user ids :::>>', user_ids)
				for user_obj in user_ids:
					lst = []
					total_commission = 0.00
					total_uplift = 0.00
					total_usage = 0
					total_broker_commission = 0.00
					supp_list = []
					lst_contract = []
					supplier_tot = 0.00
					contract_len = 0
					meter_con_len = 0
					supp_crowback_list = []
					user = ''
					contract_ids = res_contract_pool.\
						search([
						('user_id', '=', self.env.uid),
						('state', 'in', ('complete', 'livenocis_scanned', 'payment_confirm', 'query', 'admin_query')),
								('livenocis', '>=', rec.date_from),
								('livenocis', '<=', rec.date_to)])
					print ('---print contract ids ::>>>>>>>', contract_ids)
					contract_len = len(contract_ids)
					comm_pool = self.env['contract.commission.confi']
					user_id = self.env['res.users'].search([('id', '=', self.env.uid)])
					final_lst = []
					datas = {
						'year_duration': 12,  # contract_ids.year_duration
						'start_date': rec.date_from,  # contract_ids.year_duration
						'end_date': rec.date_to,  # contract_ids.year_duration
						'year': 'New Year Eve',
						'user': user_id.name,
						# 'supplier_id': contract_ids.supplier_id.name,
					}
					final_lst.append(datas)
					if contract_ids:
						for contract in contract_ids:
							comm_tot = 0.0
							broker_split = (contract.default_section_id and float(
								contract.default_section_id.broker_split) / 100) or 1
							upfront_payment = (contract.default_section_id and float(
								contract.default_section_id.upfront_payment) / 100) or 1
							commi_year = \
								comm_pool.search([('year_duration', '=', contract.year_duration), (
									'supplier_id', '=', contract.supplier_id.id), ('external_broker', '=', True)])
							print ('--print commi year ::>>>>', commi_year.percentage)
							supplier_contract_commission = commi_year.percentage
							if rec.mpan_bool:
								mpan_temp = True
								for mpan in contract.meter_data_id:
									commission_amt = 0.00
									if contract.year_duration:
										broker_upfront_per = contract.supplier_id and contract.supplier_id.BrokerUpfrontPercentage
										com = (mpan.product_uom_qty * mpan.uplift_value * int(contract.year_duration))
										con_amt = ((com != 0 and (
										com / 100) or 0.00) * contract.default_section_id.broker_split) / 100
										if contract.broker_commission_payment_quant == 'monthly':
											commission_amt = ((
															mpan.product_uom_qty * mpan.uplift_value * broker_split) / 100) / 12
										# print 'commission amount needs to be printed ::>>>>>', commission_amt
										elif contract.broker_commission_payment_quant == 'annually':
											commission_amt = (((
											com != 0 and (com / 100) or 0.00) * broker_split * upfront_payment) /
											int(contract.year_duration)) * (broker_upfront_per != 0 and broker_upfront_per / 100 or 1)
										elif contract.broker_commission_payment_quant == 'upfront':
											commission_amt = \
												mpan.product_uom_qty * contract.broker_uplift * int(
													contract.year_duration) * (upfront_payment * 100) * (
												broker_split * 100) * supplier_contract_commission / pow(10, 8)
										else:
											commission_amt = ((con_amt * broker_split * upfront_payment * (
											contract.broker_commission_percentage / 100)) / 1) \
											* (broker_upfront_per != 0 and broker_upfront_per / 100 or 1)

									res = {
										'contract_no': contract.contract_name or '',
										'cot_date': contract.cot_date or False,
										'year_duration': mpan_temp and contract.year_duration or '',
										'contract_date': contract.start_date or '',
										'commission': float(format(commission_amt, '.2f')) or 0.00,
										'contract_type': mpan_temp and (
										contract.contract_type_id and contract.contract_type_id.name) or '',
										'uplift': mpan_temp and float(contract.broker_uplift) or 0.00,
										'supplier': mpan_temp and (
										contract.supplier_id and contract.supplier_id.name) or '',
										'supplier_id': (contract.supplier_id and contract.supplier_id.id) or False,
										'usage': mpan.product_uom_qty or 0,
										'partner': mpan_temp and contract.partner_id and contract.partner_id.name or '',
										'sales_query': mpan_temp and contract.sales_query_level or '',
										'mpan_code': mpan.mpan_code or '',
										'accuracy_status': contract.broker_accuracy_checked and "True" or "False",
									}
									print ('--print res ::>>>>', res)

									meter_con_len += 1
									comm_tot += res['commission']
									total_commission += res['commission']
									total_uplift += res['uplift']
									total_usage += res['usage']
									lst.append(res)
									mpan_temp = False
							else:
								for mpan in contract.meter_data_id:
									commission_amt = 0.00
									if contract.year_duration:
										broker_upfront_per = contract.supplier_id and contract.supplier_id.BrokerUpfrontPercentage
										com = (mpan.product_uom_qty * mpan.uplift_value * int(contract.year_duration))
										con_amt = \
											((com != 0 and (com / 100) or 0.00) * contract.default_section_id.broker_split) / 100
										if contract.broker_commission_payment_quant == 'monthly':
											commission_amt = \
												((mpan.product_uom_qty * mpan.uplift_value * broker_split) / 100) / 12
										# print 'commission amount uin else condition ptrinted ::>>>',commission_amt
										elif contract.broker_commission_payment_quant == 'annually':
											commission_amt = (((com != 0 and (
											com / 100) or 0.00) * broker_split * upfront_payment) / int(
												contract.year_duration)) * \
														(broker_upfront_per != 0 and broker_upfront_per / 100 or 1)
										elif contract.broker_commission_payment_quant == 'upfront':
											commission_amt = \
												mpan.product_uom_qty * contract.broker_uplift * int(
													contract.year_duration) * (upfront_payment * 100) * (
												broker_split * 100) * supplier_contract_commission / pow(10, 8)
										else:
											commission_amt = ((con_amt * broker_split * upfront_payment * (
												contract.broker_commission_percentage / 100)) / 1) * \
															(broker_upfront_per != 0 and broker_upfront_per / 100 or 1)
									res = {
										'contract_no': contract.contract_name or '',
										'cot_date': contract.cot_date or False,
										'year_duration': contract.year_duration,
										'contract_date': contract.start_date or '',
										'commission': float(format(commission_amt, '.2f')) or 0.00,
										'contract_type': contract.contract_type_id and contract.contract_type_id.name or '',
										'uplift': float(contract.broker_uplift) or 0.00,
										'supplier': contract.supplier_id and contract.supplier_id.name or '',
										'supplier_id': contract.supplier_id and contract.supplier_id.id,
										'usage': mpan.product_uom_qty or 0,
										'partner': contract.partner_id and contract.partner_id.name or '',
										'sales_query': contract.sales_query_level or '',
										'mpan_code': '',
										'accuracy_status': contract.broker_accuracy_checked and "True" or "False",
									}

									print ('----printed res in else condiion ::>>>>',res)
									meter_con_len += 1
									comm_tot += res['commission']
									total_commission += res['commission']
									total_uplift += res['uplift']
									total_usage += res['usage']
									lst.append(res)
							if supp_list and contract.supplier_id.id in [x['supplier_id'] for x in supp_list]:
								for l in supp_list:
									if l['supplier_id'] == contract.supplier_id.id:
										l['supp_commission'] += comm_tot or 0.00
										l['count_supp'] += 1
										l['count_meter_supp'] += len(contract.meter_data_id) or 0
							else:
								supp_dic = {
									'count_supp': contract.supplier_id and 1 or 0,
									'supp_commission': comm_tot or 0.00,
									'supplier_name': contract.supplier_id.name,
									'supplier_id': contract.supplier_id and contract.supplier_id.id,
									'count_meter_supp': len(contract.meter_data_id) or 0,
								}
								supp_list.append(supp_dic)
							supplier_tot += comm_tot
							res_contract_pool.write({
								'broker_commission_paid_bool': True,
								'broker_date_finalised': time.strftime('%Y-%m-%d %H:%M:%S'),
								'broker_commission_first_payment': comm_tot})
					broker_reconcile_ids = \
						broker_commission_pool.search([('receipt_date', '>=', rec.date_from), (
							'receipt_date', '<=', rec.date_to), ('external_reconcile_line_id.user_id', '=', user_id.id),
							('external_reconcile_line_id.default_section_id.external_broker', '=', True),
							('is_external_broker', '=', True)])
					print ('---print broker reconcile ids ::>>>', broker_reconcile_ids)
					if broker_reconcile_ids:
						print ('---in if condition ::>>>>>broker reconcile ids ::>>>', broker_reconcile_ids)
						for br_com in broker_reconcile_ids:
							br_res = {
								'contract_no':
									br_com.external_reconcile_line_id and
									br_com.external_reconcile_line_id.contract_name or '',
								'cot_date': br_com.external_reconcile_line_id.cot_date or False,
								'year_duration':
									br_com.external_reconcile_line_id and
									br_com.external_reconcile_line_id.year_duration or '',
								'commission': float(format(br_com.comm_amount, '.2f')) or 0.00,
								'contract_type':
									(br_com.external_reconcile_line_id and br_com.external_reconcile_line_id.contract_type_id) and
									br_com.external_reconcile_line_id.contract_type_id.name or '',
								'uplift': br_com.external_reconcile_line_id and float(
									format(br_com.external_reconcile_line_id.broker_uplift, '.2f')) or 0.00,
								'receipt_date': br_com.receipt_date,
								'rec_ref': br_com.receipt_reference,
								'supplier':
									(br_com.external_reconcile_line_id and br_com.external_reconcile_line_id.supplier_id) and
									br_com.external_reconcile_line_id.supplier_id.name or '',
								'supplier_id':
									(br_com.external_reconcile_line_id and br_com.external_reconcile_line_id.supplier_id) and
									br_com.external_reconcile_line_id.supplier_id.id or '',
								'usage': br_com.external_reconcile_line_id and br_com.external_reconcile_line_id.usage or 0,
								'partner': br_com.external_reconcile_line_id and br_com.external_reconcile_line_id.partner_id.name or '',
								'mpan_code': '',
								'accuracy_status': br_com.external_reconcile_line_id and (
									br_com.external_reconcile_line_id.broker_accuracy_checked
									and "True" or "False"),
							}
							if rec.mpan_bool:
								meter_line = br_com.external_reconcile_line_id.meter_data_id or False
								if meter_line:
									br_res.update({'mpan_code': meter_line.mpan_code})
							total_broker_commission += br_res['commission']
							lst_contract.append(br_res)
							if supp_crowback_list and br_com.external_reconcile_line_id.supplier_id.name \
									in [x['supplier_name'] for x in supp_crowback_list]:
								for s_cb in supp_crowback_list:
									if s_cb['supplier_id'] == br_com.external_reconcile_line_id.supplier_id.id:
										s_cb['supp_commission'] += float(format(br_com.comm_amount, '.2f')) or 0.00
										s_cb['count_supp'] += 1
										s_cb['count_meter_supp'] += len(
											br_com.external_reconcile_line_id.meter_data_id) or 0
							else:
								supp_crowbackdic = {
									'count_supp': br_com.external_reconcile_line_id.supplier_id and 1 or 0,
									'supp_commission': float(format(br_com.comm_amount, '.2f')) or 0.00,
									'supplier_name': br_com.external_reconcile_line_id.supplier_id.name,
									'supplier_id': br_com.external_reconcile_line_id.supplier_id.id,
									'count_meter_supp':
										len(
											br_com.external_reconcile_line_id.meter_data_id) or 0,
								}
								supp_crowback_list.append(supp_crowbackdic)
					order_by_spp = self.get_order_by_supplier(lst)
					contract_mpan_count = self.get_counts(contract_ids)
					paid_comm = float(
						float(format(total_commission, '.2f')) + float(format(total_broker_commission, '.2f')))
					vat = float(rec.vatable and paid_comm * (section_obj.vat_rate / 100) or 0.00)
					user_dic = {
						'user': user_obj.name or '', 'lst': order_by_spp,
						'supp_crowback_list': supp_crowback_list,
						'supp_list': supp_list,
						'lst_contract': lst_contract,
						'total_broker_commission': float(format(total_broker_commission, '.2f')),
						'supplier_tot': float(format(supplier_tot, '.2f')),
						'total_uplift': float(total_uplift != 0 and contract_len != 0 and format(
							total_uplift / contract_len, '.2f')) or 0.00,
						'total_commission': float(format(total_commission, '.2f')),
						'average_tot': float(total_commission != 0 and contract_len != 0 and format(
							total_commission / contract_len, '.2f')) or 0.00,
						'total_usage': total_usage, 'cont_count': contract_mpan_count,
						'vat': format(vat, '.2f'),
						'grand_total': rec.vatable and float(format(paid_comm + vat, '.2f')) or '',
						'vat_bool': rec.vatable,
						'contract_len': int(contract_len),
						'meter_con_len': int(meter_con_len),
						'paid_commission': paid_comm,
						'basic_total_uplift': float(format(total_uplift, '.2f')),
					}
					user_list.append(user_dic)
					print ('---print user list at line 435::::>>>>>>>>', user_list)
					supp_list and self.all_supplier_list.append(supp_list)
					supp_crowback_list and self.all_supplier_adj_list.append(supp_crowback_list)

				self.manage_user_list = self.get_user_wise_data(user_list)
				self.total_commission_mac = total_commission
				self.total_broker_commission_mac = total_broker_commission
				print ('--print manage user lst ::>>>', self.manage_user_list)

			return user_list

	
	def get_user_wise_data(self, user_list):
		manage_user_lst = []
		self.user_tot_commission = 0.00
		self.user_average_tot = 0.00
		self.user_total_uplift = 0.00
		self.user_total_usage = 0
		self.all_users_total_broker_commission = 0.00
		self.all_paid_commission = 0.00
		self.all_users_vat_total = 0
		self.all_user_grand_total = 0.00
		temp_user_total_uplift = 0.00
		contract_len = 0
		if user_list:
			print ('---print user list ::::>>>', user_list)
			for u_lst in user_list:
				print ('---print manage user list ::>>>', manage_user_lst)
				if manage_user_lst and u_lst['user'] in [x['user_name'] for x in manage_user_lst]:
					for u_l in manage_user_lst:
						print ('--printing user total commission before calculation:>>>>>>', u_l['user_tot_commission'])
						if u_l['user_name'] == u_lst['user']:
							u_l['user_tot_commission'] = u_l['user_tot_commission'] + (
							u_lst['total_commission'] + u_lst['total_broker_commission']) or 0.00
						print ('---print ing user total commission:::>>>>>', u_l['user_tot_commission'])
				else:
					manage_user_dic = {
						'contract_no': u_lst['contract_len'],
						'meter_co_no': u_lst['meter_con_len'],
						'user_name': u_lst['user'],
						'user_tot_commission': float(
							format(float(u_lst['total_commission'] + u_lst['total_broker_commission']), '.2f')) or 0.00,
					}
					manage_user_lst.append(manage_user_dic)
				print ('print manage user list at end of the condition ::>>>', manage_user_lst)

				self.user_tot_commission += float(format((u_lst['total_commission']), '.2f')) or 0.00
				print ('--print user tot commission ::>>>>>', self.user_tot_commission)
				temp_user_total_uplift += float(format(float(u_lst['basic_total_uplift']), '.2f')) or 0.00
				self.user_total_usage += float(format(float(u_lst['total_usage']), '.2f')) or 0.00
				self.all_users_total_broker_commission += u_lst['total_broker_commission'] and u_lst[
					'total_broker_commission'] or 0.00
				self.all_paid_commission += u_lst['paid_commission'] and float(
					format(float(u_lst['paid_commission']), '.2f')) or 0.00
				self.all_users_vat_total += u_lst['vat'] and float(format(float(u_lst['vat']), '.2f')) or 0
				self.all_user_grand_total += u_lst['grand_total'] and float(u_lst['grand_total']) or 0.00
				contract_len += int(u_lst['contract_len']) or 0
			self.user_average_tot += contract_len and (self.user_tot_commission / contract_len) or 0.00
			self.user_total_uplift += contract_len and (temp_user_total_uplift / contract_len) or 0.00
		print ('---printed :::manage user lst end of the mthod ::>>>>::>>>>', manage_user_lst)
		return manage_user_lst

	
	def get_managed_user_list(self):
		self.get_data()
		return self.manage_user_list

	
	def get_user_average_tot(self):
		print ('--print user average total ::>>>', self.user_average_tot)
		return self.user_average_tot

	
	def get_user_total_uplift(self):
		print ('--print user total uplift ::>>>>', self.user_total_uplift)
		return self.user_total_uplift

	
	def get_user_total_usage(self):
		print ('---print user total usage ::>>>', self.user_total_usage)
		return self.user_total_usage

	
	def get_user_tot_commission(self):
		print ('--print user tot commissiondwdkldlkhdlqwdhl ::>>', self.user_tot_commission)
		return self.user_tot_commission

	
	def get_all_users_total_broker_commission(self):
		print ('--print all users total broker commission ::>>>', self.all_users_total_broker_commission)
		return self.all_users_total_broker_commission

	
	def get_all_users_paid_commission(self):
		print ('---all paid commission ::>>>>', self.all_paid_commission)
		return self.all_paid_commission

	
	def get_all_users_vat_total(self):
		return self.all_users_vat_total

	
	def get_all_user_grand_total(self):
		return self.all_user_grand_total

	
	def get_total_commission_mac(self):
		return self.total_commission_mac

	
	def get_total_broker_commission_mac(self):
		return self.total_broker_commission_mac

	
	def get_order_by_supplier(self, cont_lst):

		order_spp = []
		order_spp_dic = {}
		for data in cont_lst:
			print ('--print order suppp::>>>>', order_spp)
			# print ('--print data ::>>>>', data)
			# print ('--print x keys and :>>>>>', [x.keys() for x in order_spp])
			if data['supplier_id'] in [x.keys() for x in order_spp]:
				for l in order_spp:
					if data['supplier_id'] in l.keys():
						l[data['supplier_id']].append({
							'contract_no': data['contract_no'],
							'year_duration': data['year_duration'],
							'contract_date': data['contract_date'],
							'commission': float(format(data['commission'], '.2f')),
							'contract_type': data['contract_type'],
							'uplift': float(data['uplift']),
							'usage': int(data['usage']),
							'partner': data['partner'],
							'supplier_id': data['supplier_id'],
							'supplier': data['supplier'],
							'sales_query': data['sales_query'],
							'mpan_code': data['mpan_code'],
							'accuracy_status': data['accuracy_status'],
							'cot_date': data['cot_date']
						})
			else:
				order_spp_dic = {
					data['supplier_id']: [data]}
				order_spp.append(order_spp_dic)
		return order_spp

	def print_report_xls(self):
		for data in self:
			# today = datetime.strftime(data['date_from'], "%Y-%m-%d")
			date_ref = data.date_from.strftime('%Y') + '_' + data.date_from.strftime('%m')
			print ('---print ref date:::>>>>>', date_ref)

			report_name = 'Broker_Commission_Report(All)_%s' % (str(date_ref))

			print ('---report name:::>>>>', report_name)
			return {
				'type': 'ir.actions.report.xml',
				'report_name': 'dernetz.contract_broker_commission_reconcile',
				# 'datas': data,
				'name': report_name
			}
			# return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
