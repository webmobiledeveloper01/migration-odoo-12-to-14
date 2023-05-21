from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import osv
import urllib3
import json
import base64
import httplib2
import tempfile
# import xmlrpclib
from xmlrpc import client as xmlrpclib


class DocusignConfig(models.Model):
	_name = 'docusign.config'
	_inherit = ['mail.thread']
	_description = "Docusign Configuration"

	name = fields.Char(string='Description', states={'draft': [('readonly', False)]})
	docusign_user = fields.Char(string='Username', size=64, help="username for Docusign \ authentication", required=True)
	docusign_pass = fields.Char(string='Password', size=64, help="password for Docusign \ authentication", required=True)
	docusign_key = fields.Char(string='API Key', size=128, help="Key for Docusign \ authentication", required=True)
	docusign_baseurl = fields.Char(string='BaseUrl', size=128, help="This is the baseUrl \ for docusign", readonly=True)
	docusign_acc_no = fields.Integer(string='Account Id', readonly=True)
	docusign_authstr = fields.Char(string='Docusign Authstr', size=256, readonly=True)
	state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], 'State', readonly=True)
	url = fields.Char(string='URL', size=64, help="url for docusign server", required=True)

	# 
	# def docusign_login(self,username, password, api_key, url,):
	#     authenticateStr = "<DocuSignCredentials>" \
	#                       "<Username>" + username + "</Username>" \
	#                       "<Password>" + password + "</Password>" \
	#                       "<IntegratorKey>" + api_key + "</IntegratorKey>" \
	#                       "</DocuSignCredentials>"
	#     http = urllib3.PoolManager()
	#     r = http.request('GET', 'http://httpbin.org/robots.txt')
	#
	#     headers = {'X-DocuSign-Authentication': authenticateStr,
	#                'Accept': 'application/json'}
	#
	#     return True

	
	def create_envelope(self, login, recipient, body, subject, file_lst, signature,
						xoff, yoff, datesigned, xoff_date, yoff_date):
		rec_email = recipient.email
		rec_name = recipient.name
		body = body.encode('ascii', 'ignore')
		if datesigned:
			if len(file_lst) > 1:
				if len(file_lst) == 3:
					envelopeDef = "{\"emailBlurb\":\"" + str(body) + "\"," + \
									"\"emailSubject\":\"" + str(subject) + \
									"\"," + "\"documents\":[{" + \
									"\"documentId\":\"1\"," + \
									"\"name\":\"" + str(file_lst[0]) + "\"},{" + \
									"\"documentId\":\"2\"," + \
									"\"name\":\"" + str(file_lst[1]) + "\"},{" + \
									"\"documentId\":\"3\"," + \
									"\"name\":\"" + str(file_lst[2]) + "\"}]," + \
									"\"recipients\":{" + \
									"\"signers\":[{" + \
									"\"email\":\"" + str(rec_email) + "\"," + \
									"\"name\":\"" + str(rec_name) + " \"," + \
									"\"recipientId\":\"1\"," + \
									"\"tabs\":{" + \
									"\"dateSignedTabs\": [{" + \
									"\"anchorString\": \"" + str(datesigned) + \
									"\", " + "\"anchorXOffset\": \"" + str(xoff_date) + "\", " + \
									"\"anchorYOffset\": \"" + str(yoff_date) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]," + \
									"\"signHereTabs\":[{" + \
									"\"anchorString\": \"" + str(signature) + \
									"\", " + "\"anchorXOffset\": \"" + str(xoff) + "\", " + \
									"\"anchorYOffset\": \"" + str(yoff) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]}}]}," + \
									"\"status\":\"sent\"}"
					my_boundary_lst = []
					count = 0
					for file in file_lst:
						count += 1
						fileContents = open(file, "rb").read()
						my_boundary = "\r\n\r\n--MYBOUNDARY\r\n" + \
										"Content-Transfer-Encoding: base64\r\n" + \
										"Content-Type: application/pdf\r\n" + \
										"Content-Disposition: file; filename=\"" + \
										str(file) + "\"; documentId=" + str(count) + "\r\n" + \
										"\r\n" + \
										fileContents.decode("utf-8") + "\r\n"
						my_boundary_lst.append(my_boundary)
					requestBody = "\r\n\r\n--MYBOUNDARY\r\n" + \
									"Content-Type: application/json\r\n" + \
									"Content-Disposition: form-data\r\n" + \
									"\r\n" + \
									envelopeDef + my_boundary_lst[0] + my_boundary_lst[1] + \
									my_boundary_lst[2] + \
									"--MYBOUNDARY--\r\n\r\n"
				else:
					envelopeDef = "{\"emailBlurb\":\"" + str(body) + "\"," + \
									"\"emailSubject\":\"" + str(subject) + "\"," + \
									"\"documents\":[{" + \
									"\"documentId\":\"1\"," + \
									"\"name\":\"" + str(file_lst[0]) + "\"},{" + \
									"\"documentId\":\"2\"," + \
									"\"name\":\"" + str(file_lst[1]) + "\"}]," + \
									"\"recipients\":{" + \
									"\"signers\":[{" + \
									"\"email\":\"" + str(rec_email) + "\"," + \
									"\"name\":\"" + str(rec_name) + " \"," + \
									"\"recipientId\":\"1\"," + \
									"\"tabs\":{" + \
									"\"dateSignedTabs\": [{" + \
									"\"anchorString\": \"" + str(datesigned) + \
									"\", " + "\"anchorXOffset\": \"" + \
									str(xoff_date) + "\", " + \
									"\"anchorYOffset\": \"" + \
									str(yoff_date) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]," + \
									"\"signHereTabs\":[{" + \
									"\"anchorString\": \"" + \
									str(signature) + "\", " + \
									"\"anchorXOffset\": \"" + str(xoff) + "\", " + \
									"\"anchorYOffset\": \"" + str(yoff) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]}}]}," + \
									"\"status\":\"sent\"}"

					my_boundary_lst = []
					count = 0
					for file in file_lst:
						count += 1
						fileContents = open(file, "rb").read()
						fileContents = fileContents.decode("utf-8")
						my_boundary = "\r\n\r\n--MYBOUNDARY\r\n" + \
										"Content-Transfer-Encoding: base64\r\n" + \
										"Content-Type: application/pdf\r\n" + \
										"Content-Disposition: file; filename=\"" + \
										str(file) + "\"; documentId=" + str(count) + "\r\n" + \
										"\r\n" + \
										fileContents.decode("utf-8") + "\r\n"
						my_boundary_lst.append(my_boundary)
					requestBody = "\r\n\r\n--MYBOUNDARY\r\n" + \
									"Content-Type: application/json\r\n" + \
									"Content-Disposition: form-data\r\n" + \
									"\r\n" + \
									envelopeDef + my_boundary_lst[0] + \
									my_boundary_lst[1] + \
									"--MYBOUNDARY--\r\n\r\n"

			else:
				envelopeDef = "{\"emailBlurb\":\"" + str(body) + "\"," + \
								"\"emailSubject\":\"" + str(subject) + "\"," + \
								"\"documents\":[{" + \
								"\"documentId\":\"1\"," + \
								"\"name\":\"" + str(file_lst[0]) + "\"}]," + \
								"\"recipients\":{" + \
								"\"signers\":[{" + \
								"\"email\":\"" + str(rec_email) + "\"," + \
								"\"name\":\"" + str(rec_name) + " \"," + \
								"\"recipientId\":\"1\"," + \
								"\"tabs\":{" + \
								"\"dateSignedTabs\": [{" + \
				                "\"anchorString\": \"" + str(datesigned) + "\", \
								"+ "\"anchorXOffset\": \"" + str(xoff_date) + \
								"\", " + "\"anchorYOffset\": \"" + \
								str(yoff_date) + "\"," + \
								"\"anchorIgnoreIfNotPresent\": \"false\"," + \
								"\"anchorUnits\": \"inches\"" + "}]," + \
								"\"signHereTabs\":[{" + \
								"\"anchorString\": \"" + \
								str(signature) + "\", " + \
								"\"anchorXOffset\": \"" + str(xoff) + "\", " + \
								"\"anchorYOffset\": \"" + str(yoff) + "\"," + \
								"\"anchorIgnoreIfNotPresent\": \"false\"," + \
								"\"anchorUnits\": \"inches\"" + "}]}}]}," + \
								"\"status\":\"sent\"}"
				my_boundary_lst = []
				count = 0
				for file in file_lst:
					count += 1
					fileContents = open(file, "rb").read()
					my_boundary = "\r\n\r\n--MYBOUNDARY\r\n" + \
									"Content-Transfer-Encoding: base64\r\n" + \
									"Content-Type: application/pdf\r\n" + \
									"Content-Disposition: file; filename=\"" + str(file) + \
									"\"; documentId=" + str(count) + "\r\n" + \
									"\r\n" + \
									fileContents.decode("utf-8") + "\r\n"
					my_boundary_lst.append(my_boundary)
				requestBody = "\r\n\r\n--MYBOUNDARY\r\n" + \
								"Content-Type: application/json\r\n" + \
								"Content-Disposition: form-data\r\n" + \
								"\r\n" + \
								envelopeDef + my_boundary_lst[0] + \
								"--MYBOUNDARY--\r\n\r\n"
		else:

			if len(file_lst) > 1:
				if len(file_lst) == 3:
					envelopeDef = "{\"emailBlurb\":\"" + str(body) + "\"," + \
									"\"emailSubject\":\"" + str(subject) + "\"," + \
									"\"documents\":[{" + \
									"\"documentId\":\"1\"," + \
									"\"name\":\"" + str(file_lst[0]) + "\"},{" + \
									"\"documentId\":\"2\"," + \
									"\"name\":\"" + str(file_lst[1]) + "\"},{" + \
									"\"documentId\":\"3\"," + \
									"\"name\":\"" + str(file_lst[2]) + "\"}]," + \
									"\"recipients\":{" + \
									"\"signers\":[{" + \
									"\"email\":\"" + str(rec_email) + "\"," + \
									"\"name\":\"" + str(rec_name) + " \"," + \
									"\"recipientId\":\"1\"," + \
									"\"tabs\":{" + \
									"\"dateSignedTabs\": [{" + \
									"\"anchorString\": \"" + \
									str(datesigned) + "\", " + \
									"\"anchorXOffset\": \"" + str(xoff_date) + \
									"\", " + "\"anchorYOffset\": \"" + \
									str(yoff_date) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]," + \
									"\"signHereTabs\":[{" + \
									"\"anchorString\": \"" + str(signature) + \
									"\", " + "\"anchorXOffset\": \"" + \
									str(xoff) + "\", " + "\"anchorYOffset\": \"" + \
									str(yoff) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]}}]}," + \
									"\"status\":\"sent\"}"
					my_boundary_lst = []
					count = 0
					for file in file_lst:
						# print ('--print file in else condition of file not signed in file list == 3', file)
						count += 1
						fileContents = open(file, "rb").read()
						my_boundary = "\r\n\r\n--MYBOUNDARY\r\n" + \
										"Content-Type: application/pdf\r\n" + \
										"Content-Transfer-Encoding: base64\r\n" + \
										"Content-Disposition: file; filename=\"" + \
										str(file) + "\"; documentId=" + \
										str(count) + "\r\n" + \
										"\r\n" + \
										fileContents.decode("utf-8") + "\r\n"
						my_boundary_lst.append(my_boundary)
					requestBody = "\r\n\r\n--MYBOUNDARY\r\n" + \
									"Content-Type: application/json\r\n" + \
									"Content-Disposition: form-data\r\n" + \
									"\r\n" + \
									envelopeDef + my_boundary_lst[0] + \
									my_boundary_lst[1] + my_boundary_lst[2] + \
									"--MYBOUNDARY--\r\n\r\n"
				else:
					envelopeDef = "{\"emailBlurb\":\"" + str(body) + "\"," + \
									"\"emailSubject\":\"" + \
									str(subject) + "\"," + "\"documents\":[{" + \
									"\"documentId\":\"1\"," + \
									"\"name\":\"" + str(file_lst[0]) + "\"},{" + \
									"\"documentId\":\"2\"," + \
									"\"name\":\"" + str(file_lst[1]) + "\"}]," + \
									"\"recipients\":{" + \
									"\"signers\":[{" + \
									"\"email\":\"" + str(rec_email) + "\"," + \
									"\"name\":\"" + str(rec_name) + " \"," + \
									"\"recipientId\":\"1\"," + \
									"\"tabs\":{" + \
									"\"signHereTabs\":[{" + \
									"\"anchorString\": \"" + \
									str(signature) + "\", " + \
									"\"anchorXOffset\": \"" + str(xoff) + \
									"\", " + \
									"\"anchorYOffset\": \"" + str(yoff) + "\"," + \
									"\"anchorIgnoreIfNotPresent\": \"false\"," + \
									"\"anchorUnits\": \"inches\"" + "}]}}]}," + \
									"\"status\":\"sent\"}"

					my_boundary_lst = []
					count = 0
					for file in file_lst:
						# print ('else condition file not signed else condition filelist ==3 :::>>>> file printed ', file)
						count += 1
						fileContents = open(file, "rb").read()
						my_boundary = "\r\n\r\n--MYBOUNDARY\r\n" + \
										"Content-Transfer-Encoding: base64\r\n" + \
										"Content-Type: application/pdf\r\n" + \
										"Content-Disposition: file; filename=\"" + \
										str(file) + "\"; documentId=" + str(count) + "\r\n" + \
										"\r\n" + \
										fileContents.decode("utf-8") + "\r\n"
						my_boundary_lst.append(my_boundary)
					requestBody = "\r\n\r\n--MYBOUNDARY\r\n" + \
									"Content-Type: application/json\r\n" + \
									"Content-Disposition: form-data\r\n" + \
									"\r\n" + \
									envelopeDef + my_boundary_lst[0] + \
									my_boundary_lst[1] + \
									"--MYBOUNDARY--\r\n\r\n"
			else:
				envelopeDef = "{\"emailBlurb\":\"" + str(body) + "\"," + \
								"\"emailSubject\":\"" + str(subject) + "\"," + \
								"\"documents\":[{" + \
								"\"documentId\":\"1\"," + \
								"\"name\":\"" + str(file_lst[0]) + "\"}]," + \
								"\"recipients\":{" + \
								"\"signers\":[{" + \
								"\"email\":\"" + str(rec_email) + "\"," + \
								"\"name\":\"" + str(rec_name) + " \"," + \
								"\"recipientId\":\"1\"," + \
								"\"tabs\":{" + \
								"\"signHereTabs\":[{" + \
								"\"anchorString\": \"" + \
								str(signature) + "\", " + \
								"\"anchorXOffset\": \"" + str(xoff) + "\", " + \
								"\"anchorYOffset\": \"" + str(yoff) + "\"," + \
								"\"anchorIgnoreIfNotPresent\": \"false\"," + \
								"\"anchorUnits\": \"inches\"" + "}]}}]}," + \
								"\"status\":\"sent\"}"

				# if we remove anchorXOffset,anchorYOffset,anchorIgnoreIfNotPresent
				my_boundary_lst = []
				count = 0
				for file in file_lst:
					# print ('else condition file not sined file list > 1 else ::>>> file printed  ', file)
					count += 1
					fileContents = open(file, "rb").read()
					fileContents = fileContents.decode("ascii")
					my_boundary = "\r\n\r\n--MYBOUNDARY\r\n" + \
									"Content-Transfer-Encoding: base64\r\n" + \
									"Content-Type: application/pdf\r\n" + \
									"Content-Disposition: file; filename=\"" + \
									str(file) + "\"; documentId=" + str(count) + "\r\n" + \
									"\r\n" + \
									(fileContents) + "\r\n"
					# base64.b64encode
					my_boundary_lst.append(my_boundary)
				requestBody = "\r\n\r\n--MYBOUNDARY\r\n" + \
								"Content-Type: application/json\r\n" + \
								"Content-Disposition: form-data\r\n" + \
								"\r\n" + \
								envelopeDef + my_boundary_lst[0] + \
								"--MYBOUNDARY--\r\n\r\n"
		url = login['baseurl'] + "/envelopes"
		headers = {'X-DocuSign-Authentication': login['auth_str'],
					'Content-Type': 'multipart/form-data; boundary=MYBOUNDARY',
					'Accept': 'application/json'}
		http = httplib2.Http('/tmp/', disable_ssl_certificate_validation=True)
		try:
			response, content = http.request(
				url, 'POST', headers=headers, body=requestBody)
		except Exception as e:
			raise ValidationError("Invalid Data %s" % e)
		return response, content

	
	def req_env_status_url(self, login, envid):
		url = login['baseurl'] + '/envelopes?envelopeId=' + envid
		headers = {'X-DocuSign-Authentication': login['auth_str'], 'Accept': 'application/json'}
		http = httplib2.Http('/tmp/', disable_ssl_certificate_validation=True)
		try:
			response, content = http.request(url, 'GET', headers=headers)
		except Exception as e:
			raise ValidationError("Invalid Data %s" % e)
		return response, content

	
	def docusign_login(self, username, password, api_key, url):
		authenticateStr = "<DocuSignCredentials>" \
						  "<Username>" + username + "</Username>" \
													"<Password>" + password + "</Password>" \
																			  "<IntegratorKey>" + api_key + "</IntegratorKey>" \
																											"</DocuSignCredentials>"

		headers = {'X-DocuSign-Authentication': authenticateStr, 'Accept': 'application/json'}
		print('----print headerc:::::>>>>>>>>>', headers)
		http = httplib2.Http('/tmp/', disable_ssl_certificate_validation=True)
		try:
			response, content = http.request(url, 'GET', headers=headers)
		except Exception as e:
			# raise osv.except_osv(('Invalid Data!'), ("%s.") % (e))
			raise ValidationError("Invalid Data %s" % e)
		return response, content, authenticateStr

	
	def req_decline_env_status(self, login, envid):
		url = login['baseurl'] + '/envelopes/' + envid + '/recipients'
		headers = {'X-DocuSign-Authentication': login['auth_str'], 'Accept': 'application/json'}
		http = httplib2.Http('/tmp/', disable_ssl_certificate_validation=True)
		try:
			response, content = http.request(url, 'GET', headers=headers)
		except Exception as e:
			raise ValidationError("Invalid Data %s" % e)
		return response, content

	
	def download_documents(self, login, req_info):
		url = login['baseurl'] + req_info + "/documents"
		headers = {'X-DocuSign-Authentication': login['auth_str'], 'Accept': 'application/json'}
		http = httplib2.Http('/tmp/', disable_ssl_certificate_validation=True)
		try:
			response, content = http.request(url, 'GET', headers=headers)
		except Exception as e:
			raise ValidationError("Invalid Data %s" % e)
			#     status = response.get('status');
		if response.get('status') != '200':
			return response, content, False
		# print ('---content 455 printed :::>>>>',content)
		string_data = content.decode('utf-8')
		# print ('----string data converted and printed after 455:::>>>>>',string_data)
		data = json.loads(string_data)
		envelopeDocs = data.get('envelopeDocuments')
		uriList = []
		file_lst = []
		dir_lst = []
		for docs in envelopeDocs:
			uriList.append(docs.get("uri"))
			url = login['baseurl'] + uriList[len(uriList) - 1]
			headers = {'X-DocuSign-Authentication': login['auth_str']}
			http = httplib2.Http('/tmp/', disable_ssl_certificate_validation=True)
			try:
				response_doc, content_doc = http.request(
					url, 'GET', headers=headers)
			except Exception as e:
				raise ValidationError("Invalid Data %s" % e)
			if response_doc.get('status') == '200':
				file_name = docs.get("name").split('/')
				directory_name = tempfile.mkdtemp()
				if file_name and file_name[0] == 'Summary':
					filename = directory_name + "/%s" % 'certificate.pdf'
				else:
					filename = directory_name + "/%s" % (
						file_name and file_name[-1] or 'doc.pdf')
				# print ('---printed content doc 482::>>>>>>>',content_doc)
				doc_with_str_content = content_doc.decode('utf-8', 'ignore')
				# print ('----str content doc decoded::>>>>>',doc_with_str_content)
				file = open(filename, 'w')
				file.write(doc_with_str_content)
				file.close()
				file_lst.append(filename)
				dir_lst.append(directory_name)
		return response_doc, file_lst, dir_lst
