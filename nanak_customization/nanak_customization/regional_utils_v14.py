import frappe
@frappe.whitelist()
def get_gstins_for_company():
	company_gstins =[]
	company = frappe.db.get_value("Global Defaults",None,"default_company")
	if company:
		company_gstins = frappe.db.sql("""select
			distinct `tabAddress`.gstin
		from
			`tabAddress`, `tabDynamic Link`
		where
			`tabDynamic Link`.parent = `tabAddress`.name and
			`tabDynamic Link`.parenttype = 'Address' and
			`tabDynamic Link`.link_doctype = 'Company' and
			`tabDynamic Link`.link_name = %(company)s""", {"company": company})
	return company_gstins
