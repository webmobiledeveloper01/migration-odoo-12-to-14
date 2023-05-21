from datetime import date
from suds.client import Client
import xmltodict
from odoo.exceptions import ValidationError
from odoo.addons.dernetz import loqate_utils
from odoo import api, models, fields, _


class WizMpnnSearch(models.TransientModel):
    _name = 'wiz.mpnn.search'
    _description = "Wiz MPNN Search"
    _rec_name = 'street'

    mpan_num = fields.Char('MPAN Number')
    mpr_num = fields.Char('MPR Number')
    street = fields.Char('Street')
    street2 = fields.Char('Street 2')
    town = fields.Char('Town')
    county = fields.Char('County')
    zip = fields.Char('Zip')
    country = fields.Char('Country')
    partner_id = fields.Many2one('res.partner', 'Partner')
    # mpnn_search_line = fields.One2many(
    #     'wiz.mpnn.search.line', 'mpnn_search_id', 'MPNN Search Lines')
    mpnn_find_line = fields.One2many('wiz.mpnn.find.line', 'mpnn_find_id', string='MPNN Search Lines')

    @api.model
    def default_get(self, fields):
        res = super(WizMpnnSearch, self).default_get(fields)
        partner_obj = self.env['res.partner']
        for partner_data in partner_obj.browse([self._context.get('active_id')]):
            res.update({'street': partner_data.street or '',
                        'street2': partner_data.street2 or '',
                        'town': partner_data.city or '',
                        'county': partner_data.state_id.name or '',
                        'zip': partner_data.zip or '',
                        'country': partner_data.country_id.name or '',
                        'partner_id': partner_data.id or '', })
        return res

    
    def get_mpnn_using_wizard(self):
        res = {}
        count = 1.0
        search_line = []
        user_obj = self.env['res.users']
        search_line_obj = self.env['total.search.line']
        search_line_date_ids = search_line_obj.search(
            [('user_id', '=', self.env.uid), ('date', '=', date.today().strftime('%Y-%m-%d'))],)

        if search_line_date_ids:
            print("----search lines data ids::>>>", search_line_date_ids)
            for search_line_data in search_line_date_ids:
                search_line.append((1, search_line_data.id,
                                    {'date': date.today().strftime('%Y-%m-%d'),
                                     'search': search_line_data.search + 1}))
            res.update(search_line=search_line)
        else:
            search_line.append((0, 0, {'date':
                                       date.today().strftime('%Y-%m-%d'),
                                       'search': count}))
            res.update(search_line=search_line)
        search_line_ids = search_line_obj.search([('user_id', '=',
                                                   self.env.uid)])
        print ("----search line list custom made ::>>", search_line)
        if search_line_ids:
            total_search = 1.0
            for line_data in search_line_ids:
                total_search = total_search + line_data.search_user or 0.0
        user_obj.write(res)
        mpnn_search_line_data = self.get_mpnn_search_line()
        mpnn_search_find_obj = self.env['wiz.mpnn.find.line']
        mpnn_search_find_ids = mpnn_search_find_obj.search([('mpnn_find_id', 'in', self.ids)])
        print ("-----mpnn_seacrline ids::::>>>>>", mpnn_search_find_ids)
        if mpnn_search_find_ids:
            mpnn_search_find_ids.unlink()  # mpnn_search_find_ids
        self.write(mpnn_search_line_data)
        # self_obj_write =

        return {
            'name': 'GET MPNN',
            # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wiz.mpnn.search',
            'domain': [],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'views': [(False, 'form')],
            'res_id': self.ids[0],
        }

    
    def get_mpnn_search_line(self):
        res = {}
        for cur_data in self:
            address = "%s,%s,%s,%s" % (cur_data.street or '',
                                       cur_data.street2 or '', cur_data.zip or
                                       '', cur_data.town or '')
            key = 'XR76-JA97-KP54-HU54'
            datas = loqate_utils.capture_interactive_find_v1_10(key, address)
            print ("data>>>", datas)

            for data in datas:
                if data.get('Type') == 'Postcode' and data.get('Id'):
                    datas = loqate_utils.capture_interactive_find_v1_10(key, address, True, data.get('Id'))
                    # print "PC data>>>", len(datas)
                    mpnn_search_line = []
                    for data in datas:
                        if data.get('Type') == 'Address' and data.get('Id'):
                            fields_data = {
                                'add_id': data.get('Id'),
                                'line1': data.get('Text'),
                                'line2': data.get('Description'),
                            }
                        mpnn_search_line.append((0, 0, fields_data))
                    res.update(mpnn_find_line=mpnn_search_line)
                if data.get('Error') and data.get('Cause'):
                    raise ValidationError("Failed %s" % data.get('Cause'))
        return res


def get_detailed_address(key, add_id):
    address_details = loqate_utils.capture_interactive_retrieve_v1_00(key, add_id)
    print ("address_details>>>>>", address_details)
    address_details = address_details[0]

    if address_details.get('Error') and address_details.get('Cause'):
        raise ValidationError("Failed %s" % address_details.get('Cause'))

    wiz_electric_line = []
    wiz_gas_line = []

    fields_data = {
        'fore': address_details.get('fore'),
        'surn': address_details.get('surn'),
        'dept': address_details.get('Department'),
        'orgn': address_details.get('Company'),
        'pobx': address_details.get('PostalCode'),
        'subb': address_details.get('SubBuilding'),
        'bnam': address_details.get('BuildingName') or address_details.get('Street'),
        'bnum': address_details.get('BuildingNumber'),
        'thor': address_details.get('District'),
        'town': address_details.get('City'),
        'cnty': address_details.get('ProvinceName'),
        'ppco': address_details.get('PostalCode'),
        'tpco': address_details.get('PostalCode'),
        'pcod': address_details.get('PostalCode'),
        'fuel': address_details.get('Field43'),
        'lguf': address_details.get('Field84'),
        'ctmn': address_details.get('Field105'),
        'ctmp': address_details.get('Field147'),
    }

    if fields_data.get('ctmn') and int(fields_data.get('ctmn')) >= 1:
        mp_value = False
        sm_value = False
        mt_value = False
        tl_value = False
        for i in range(int(fields_data.get('ctmn'))):
            i += 1
            for k, v in loqate_utils.fieldsformat.items():
                k = k.replace('format', '').capitalize()
                if v == 'MPAN' + str(i):
                    mp_value = address_details.get(k)
                if v == 'ElectricMeterSerial' + str(i):
                    sm_value = address_details.get(k)
                if v == 'ElectricMeterType' + str(i):
                    mt_value = address_details.get(k)
                if v == 'MPANTopLine' + str(i):
                    tl_value = address_details.get(k)
                if mp_value and sm_value and mt_value and tl_value:
                    break
            ele_01 = {
                'mp_value': mp_value,
                'sm_value': sm_value,
                'mt_value': mt_value,
                'tl_value': tl_value
            }
            wiz_electric_line.append((0, 0, ele_01))

    if fields_data.get('ctmp') and int(fields_data.get('ctmp')) >= 1:
        mn_value = False
        ms_value = False
        for i in range(int(fields_data.get('ctmp'))):
            i += 1
            for k, v in loqate_utils.fieldsformat.items():
                k = k.replace('format', '').capitalize()
                if v == 'MPRN' + str(i):
                    mn_value = address_details.get(k)
                if v == 'GasMeterSerial' + str(i):
                    ms_value = address_details.get(k)
                if mn_value and ms_value:
                    break
            gas_01 = {
                'mn_value': mn_value,
                'ms_value': ms_value,
            }
            wiz_gas_line.append((0, 0, gas_01))

    fields_data.update({
        'wiz_electric_line': wiz_electric_line,
        'wiz_gas_line': wiz_gas_line,
    })

    print ("fields_data", fields_data)
    return fields_data


class WizMpnnFindLine(models.TransientModel):
    _name = 'wiz.mpnn.find.line'

    mpnn_find_id = fields.Many2one('wiz.mpnn.search', 'MPNN Search')
    add_id = fields.Char('Address Id')
    line1 = fields.Char('Line 1')
    line2 = fields.Char('Line 2')

    
    def open_detailed_record(self):
        self.ensure_one()
        view_id = self.env.ref('dernetz.wiz_mpnn_search_line_form_view', False)
        data = get_detailed_address('XR76-JA97-KP54-HU54', self.add_id)
        data.update({
            'partner_id': self.mpnn_find_id.partner_id.id
        })
        res_id = self.env['wiz.mpnn.search.line'].create(data)
        return {
            'name': 'Detailed Data',
            'res_model': 'wiz.mpnn.search.line',
            'domain': [],
            'context': dict(self._context),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'views': [(view_id.id, 'form')],
            'view_id': view_id.id,
            'res_id': res_id.id,
        }


class WizMpnnSearchLine(models.TransientModel):
    _name = 'wiz.mpnn.search.line'
    _description = "Wiz MPNN Search Line"

    mpnn_search_id = fields.Many2one('wiz.mpnn.search', 'MPNN Search')
    partner_id = fields.Many2one('res.partner', 'Partner')
    fore = fields.Char('Forename')
    surn = fields.Char('Surname')
    bnam = fields.Char('Building Name')
    bnum = fields.Char('Building Number')
    town = fields.Char('Town')
    cnty = fields.Char('County')
    dept = fields.Char('Department')
    orgn = fields.Char('Organisation')
    pobx = fields.Char('PO Box')
    subb = fields.Char('Sub Building')
    pcod = fields.Char('Zip')
    thor = fields.Char('Thor')
    ppco = fields.Char('PPCO')
    tpco = fields.Char('TPCO')
    fuel = fields.Char('FUEL')
    lguf = fields.Char('LGUF')
    ctmn = fields.Char('CTMN')
    ctmp = fields.Char('CTMP')
    wiz_electric_line = fields.One2many('wiz.electric.reference', 'mpnn_search_line_id', 'Electric Meter Numbers')
    wiz_gas_line = fields.One2many('wiz.gas.reference', 'mpnn_search_line_id', 'Gas Meter Numbers')

    
    def create_record(self):
        electric_info_line_obj = self.env['electric.info.line']
        gas_info_line_obj = self.env['gas.info.line']
        vals = {}
        address1 = ''
        address2 = ''
        new_id = False
        for rec in self:
            new_id = rec.partner_id.id
            if rec.bnam and rec.subb:
                address1 = rec.bnam + '/' + rec.subb
            elif rec.bnam:
                address1 = rec.bnam
            elif rec.subb:
                address1 = rec.subb
            if rec.bnum and rec.thor:
                address2 = rec.bnum + '/' + rec.thor
            elif rec.bnum:
                address2 = rec.bnum
            elif rec.thor:
                address2 = rec.thor
            gas_lines = []
            for data_gas in rec.wiz_gas_line:
                gas_info_line_ids = gas_info_line_obj.search(
                    [('partner_id', '=', new_id)])
                if gas_info_line_ids:
                    gas_info_line_ids.unlink()
                gas_lines.append((0, 0, {'fuel_type': 'Gas',
                                         'mprn': data_gas.mn_value,
                                         'meter_serial_number':
                                         data_gas.ms_value}))
            electric_lines = []
            for data_electric in rec.wiz_electric_line:
                electric_info_line_ids = electric_info_line_obj.search(
                    [('partner_id', '=', new_id)])
                if electric_info_line_ids:
                    electric_info_line_ids.unlink()
                electric_lines.append((0, 0, {
                    'fuel_type': 'Electric',
                    'long_mpan': data_electric.tl_value[0:2] + '-' +
                    data_electric.tl_value[2:5] + '-' + data_electric.tl_value[
                        5:8] + '-' + data_electric.mp_value[0:2] + '-' +
                    data_electric.mp_value[2:6] + '-' + data_electric.mp_value[
                        6:10] + '-' + data_electric.mp_value[10:13],
                    'short_mpan': data_electric.mp_value,
                    'meter_serial_number': data_electric.sm_value,
                    'meter_type': data_electric.mt_value,
                }))
        vals = {
            'search_street': address1 or '',
            'search_street2': address2 or '',
            'town': rec.town or '',
            'search_county': rec.cnty or '',
            'search_zip': rec.ppco or '',
            'orgn': rec.orgn or '',
            'fore': rec.fore or '',
            'surn': rec.surn or '',
            'ctmn': rec.ctmn or '',
            'ctmp': rec.ctmp or '',
            'gas_info_line': gas_lines,
            'electric_info_line': electric_lines,
        }
        if rec.fuel == 'B':
            vals.update({'gas_bool': True, 'electric_bool': True})
        elif rec.fuel == 'G':
            vals.update({'gas_bool': True})
        elif rec.fuel == 'E':
            vals.update({'electric_bool': True})
        else:
            vals.update({'gas_bool': False, 'electric_bool': False})

        rec.partner_id.write(vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': new_id,
            # 'view_type': 'form',
            'view_mode': 'form,tree',
            'target': 'current',
            'nodestroy': True,
        }


class WizElectricReference(models.TransientModel):
    _name = 'wiz.electric.reference'
    _description = "Wiz Electric Reference"

    mpnn_search_line_id = \
        fields.Many2one('wiz.mpnn.search.line', 'MPNN Search Line')
    mp_value = fields.Char('Meter Point Reference Values')
    sm_value = fields.Char('Meter Serial Values')
    mt_value = fields.Char('Electric Meter Type Value')
    tl_value = fields.Char('Top Line Value')


class WizGasReference(models.TransientModel):
    _name = 'wiz.gas.reference'
    _description = "Wiz Gas Reference"

    mpnn_search_line_id = \
        fields.Many2one('wiz.mpnn.search.line', 'MPNN Search Line')
    mn_value = fields.Char('Meter Point Reference Value')
    ms_value = fields.Char('Meter Serial Values')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
