import frappe

def after_submit(self,method):
    if self.picklist_reference:
        frappe.db.set_value("Nanak Pick List", self.picklist_reference, "sales_invoice", self.name)
        frappe.db.set_value("Nanak Pick List", self.picklist_reference, "sales_invoice_status", "Created")