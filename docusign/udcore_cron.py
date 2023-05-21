from odoo import api, fields, models, _
import json
import requests
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import base64


class UdicoreDocusignCron(models.Model):
    _name = 'udicore.docusign.cron'
    _description = "Udicore Docusign Cron"

    @api.model
    def _signed_document_cron(self):
        signed_docusign = self.env['docusign.document'].search([('state', '=', 'sent')])
        print ('----signed docuemnt printed ::>>>>>', signed_docusign)
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise UserError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        else:
            print ('---print udcore apu in else condition ::>>>>', udicore_api)

            for record in signed_docusign:
                postdata = {
                    "docusignDetails": {
                        "RefID": record.ref_id, "EnvelopeID": record.env_id,
                        "SecurityDetails": {"LicenceCode": udicore_api.licence_code,
                                            "mascaradeuser": udicore_api.mascarade_user}
                    }
                }

                headers = {'content-type': 'application/json; charset=utf-8'}
                url = 'https://udcoreapi.co.uk/DocusignService.svc/web/getdocusignpdf'
                data = postdata
                aa = requests.post(url, data=json.dumps(data), headers=headers)
                aa = json.loads(aa.text)
                print ('data---------::::::::::', data)
                # print ('-----print aaa::::::::>>>>>>>>>>>>>>>>>>>>', aa)

                bytestring = ""
                PDFBytes = aa.get('GetDocusignPDFResult').get('PDFBytes')
                if PDFBytes:
                    bt = ''
                    for i in range(len(PDFBytes)):
                        bt += 'a'.join((list(map(chr, [PDFBytes[i]]))))
                    attach_ids = []
                    aa = base64.b64encode(str(bt).encode('latin-1'))
                    data_attach = {
                        'name': record.subject+'.pdf',
                        'datas': aa,
                        'datas_fname': record.subject+'.pdf',
                        'res_model': 'res.contract',
                        'res_id': record.res_id,
                        'type': 'binary',
                        'mimetype': 'application/pdf'
                        # 'index_content': '',
                    }
                    res_id = self.env['ir.attachment'].create(data_attach)
                    attach_ids.append(res_id.id)

                    # try:
                    if record.env_id:
                        record.write({'state': 'completed', 'sign_attachment_ids': [(6, 0, attach_ids)]})
                        print ("==============", record.contract_id)
                        print ('--------printing stateforr conttract-----', record.contract_id.state)
                        record.contract_id.write({'sale_confirmed_date': datetime.now().strftime("%Y%m%d %H%M%S"),
                                                  'confirmation_date': datetime.now(),
                                                  'docusign_received_datetime': datetime.now(),
                                                  'docusign_received': 'Received',
                                                  'state': 'sale_agreed'})

                    # except ValueError:
                    else:
                        record.write({'state': 'delivered'})
