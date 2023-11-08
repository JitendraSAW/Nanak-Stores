# Copyright (c) 2022, Raaj Tailor and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NanakStandardSettings(Document):
	pass


@frappe.whitelist()
def update_custom_picked_qty():
	# Update custom_picked_qty for records where picked_qty > 0
	
	query = """
	UPDATE `tabSales Order Item` soi
	SET soi.custom_picked_qty = soi.picked_qty
	where
	soi.picked_qty > 0;
	"""
	frappe.db.sql(query)
	frappe.db.commit()

	frappe.msgprint("custom_picked_qty has been updated for records where picked_qty > 0.")

