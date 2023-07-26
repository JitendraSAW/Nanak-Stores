import frappe

def after_submit(self,method):
    if self.picklist_reference:
        frappe.db.set_value("Nanak Pick List", self.picklist_reference, "sales_invoice_status", "Created")

def validate(self,method):
    if self.picklist_reference:
        frappe.db.set_value("Nanak Pick List", self.picklist_reference, "sales_invoice", self.name)
        frappe.db.commit()

def on_cancel(self,method):
    if self.picklist_reference:
        stock_picklist_doc = frappe.get_doc('Stock Entry',{'nanak_pick_list':self.picklist_reference})
        stock_picklist_doc.cancel()
        frappe.msgprint("{0}: Stock Entry Cancelled Against Nanak Pick List Created".format(stock_picklist_doc.name))
        picklist_doc = frappe.get_doc('Nanak Pick List',self.picklist_reference)
        picklist_doc.cancel()
        
        frappe.db.commit()
        frappe.msgprint("{0}:Nanak Pick List has been Cancelled".format(self.picklist_reference))