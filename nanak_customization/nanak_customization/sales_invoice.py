import frappe

def after_submit(self,method):
    if self.picklist_reference:
        frappe.db.set_value("Nanak Pick List", self.picklist_reference, "sales_invoice_status", "Created")

def validate(self,method):
    if self.picklist_reference:
        frappe.db.set_value("Nanak Pick List", self.picklist_reference, "sales_invoice", self.name)

def on_trash(self, method):
    # frappe.throw("on trash event")
    try:
        if self.picklist_reference and self.docstatus == 0:
            frappe.db.set_value("Sales Invoice", self.name, {
                "picklist_reference": ""
            })
            frappe.db.set_value("Nanak Pick List", self.picklist_reference, {
                "sales_invoice": "",
                "sales_invoice_status": ""
            })

            frappe.db.sql("""
                UPDATE `tabSales Invoice Item`
                SET nanak_pick_list = '', pick_list_details = ''
                WHERE parent = %s
            """, (self.name,))
            
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"on trash event error")

        


@frappe.whitelist()
def unlink_vouchers(nanak_pick_list, sales_invoice):
    try:
        frappe.db.set_value("Sales Invoice", sales_invoice, "picklist_reference", "")
        frappe.db.set_value("Nanak Pick List", nanak_pick_list, "sales_invoice", "")
        frappe.db.set_value("Nanak Pick List", nanak_pick_list, "sales_invoice_status", "")  
        frappe.db.commit()
        return "success"
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Unlink Vouchers Error')
        return f"error: {str(e)}"
