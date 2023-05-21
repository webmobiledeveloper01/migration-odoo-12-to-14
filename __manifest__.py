# -*- coding: utf-8 -*-
{
    'name': 'Dernetz',
    'version': '14.0.0.0',
    'description': 'Utilities Management for Dernetz',
    'depends': ['base', 'product', 'account', 'crm', 'attachment_indexation'],
    'author': 'Hasnain Devjani (razadevjani1214@gmail.com)',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/data_sequence.xml',
        # 'data/ir_cron_view.xml',
        # 'data/demo_data_supplier.xml',

        # 'demo/email_template.xml',
        # 'demo/docusign_template.xml',
        'demo/product_category_demo_data.xml',

        'views/contract_view.xml',
        'views/contract_config_view.xml',

        'wizard/add_existing_contact_wizard_view.xml',
        # 'wizard/wiz_meter_view.xml',

        'wizard/add_branch_company_view.xml',
        'wizard/add_note_by_sales_team_view.xml',
        # 'wizard/contract_commission_reconciliation_view.xml',
        # 'wizard/contract_commission_reconciliation_admin_view.xml',
        # 'wizard/contract_commission_reconciliation_view_broker_report.xml',
        # 'wizard/contract_commission_reconciliation_view_by_admin.xml',
        'wizard/contract_verbal_view.xml',
        'wizard/eon_list_contract_xls_view.xml',
        'wizard/raise_query_view.xml',
        'wizard/total_search_report_view.xml',
        'wizard/wiz_meter_bool_view.xml',


        'views/send_contract_email_view.xml',
        'views/contract_commission_config_view.xml',
        'views/contract_dashboard_view.xml',
        # 'views/sale_view.xml',
        'views/crm_inherit_view.xml',
        'views/meter_data_view.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
        'views/gb_service_config_view.xml',
        'views/res_users_view.xml',

        'wizard/wizard_sale_per_comission_view.xml',
        'wizard/years_in_resident_view.xml',


        'docusign/docusign_config_view.xml',
        'docusign/docusign_document_view.xml',
        'docusign/docusign_template_view.xml',
        'docusign/udcore_api_menu_view.xml',
        'docusign/send_docusign_wiz_view.xml',
        'docusign/docusign_mail_wizard_view.xml',
        'docusign/quick_quote_udcore_view.xml',
        'docusign/quote_wizard_view.xml',

        'report/report_price_comparision_template.xml',
        'report/price_comparisio_quote_tool.xml',
        'report/reports.xml',

    ]
}
