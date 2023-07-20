# Copyright (c) 2022, Raaj Tailor and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from pickle import TRUE
from pickletools import read_string1
import frappe
import frappe.defaults
from erpnext.controllers.selling_controller import SellingController
from erpnext.stock.doctype.batch.batch import set_batch_nos
from erpnext.stock.doctype.serial_no.serial_no import get_delivery_note_serial_no
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import cint, flt
from erpnext.controllers.accounts_controller import get_taxes_and_charges
# from console import console
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.utils import get_stock_balance
from erpnext.stock.get_item_details import get_conversion_factor, get_item_details
from erpnext.stock.get_item_details import get_bin_details
from frappe.utils.user import get_users_with_role
from frappe.utils import get_formatted_email
import json



form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class NanakPickList(SellingController):
	# override mrthod from accounts controller
	
	def __init__(self, *args, **kwargs):
		super(NanakPickList, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'source_dt': 'Nanak Pick List Item',
			'target_dt': 'Sales Order Item',
			'join_field': 'so_detail',
			'target_field': 'delivered_qty',
			'target_parent_dt': 'Sales Order',
			'target_parent_field': 'per_delivered',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'against_sales_order',
			'status_field': 'delivery_status',
			'keyword': 'Delivered',
			'second_source_dt': 'Sales Invoice Item',
			'second_source_field': 'qty',
			'second_join_field': 'so_detail',
			'overflow_type': 'delivery',
			'second_source_extra_cond': """ and exists(select name from `tabSales Invoice`
				where name=`tabSales Invoice Item`.parent and update_stock = 1)"""
		},
		{
			'source_dt': 'Nanak Pick List Item',
			'target_dt': 'Sales Invoice Item',
			'join_field': 'si_detail',
			'target_field': 'delivered_qty',
			'target_parent_dt': 'Sales Invoice',
			'target_ref_field': 'qty',
			'source_field': 'qty',
			'percent_join_field': 'against_sales_invoice',
			'overflow_type': 'delivery',
			'no_allowance': 1
		}]
		if cint(self.is_return):
			self.status_updater.extend([{
				'source_dt': 'Nanak Pick List Item',
				'target_dt': 'Sales Order Item',
				'join_field': 'so_detail',
				'target_field': 'returned_qty',
				'target_parent_dt': 'Sales Order',
				'source_field': '-1 * qty',
				'second_source_dt': 'Sales Invoice Item',
				'second_source_field': '-1 * qty',
				'second_join_field': 'so_detail',
				'extra_cond': """ and exists (select name from `tabNanak Pick List`
					where name=`tabNanak Pick List Item`.parent and is_return=1)""",
				'second_source_extra_cond': """ and exists (select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and is_return=1 and update_stock=1)"""
			},
			{
				'source_dt': 'Nanak Pick List Item',
				'target_dt': 'Nanak Pick List Item',
				'join_field': 'dn_detail',
				'target_field': 'returned_qty',
				'target_parent_dt': 'Nanak Pick List',
				'target_parent_field': 'per_returned',
				'target_ref_field': 'stock_qty',
				'source_field': '-1 * stock_qty',
				'percent_join_field_parent': 'return_against'
			}
		])

	def set_missing_item_details(self, for_validate=False):
		force_item_fields = ("item_group", "brand", "stock_uom", "is_fixed_asset", "item_tax_rate","pricing_rules", "weight_per_unit", "weight_uom", "total_weight")
		"""set missing item values"""
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		if hasattr(self, "items"):
			parent_dict = {}
			for fieldname in self.meta.get_valid_columns():
				parent_dict[fieldname] = self.get(fieldname)

			if self.doctype in ["Nanak Pick List","Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
				document_type = "{} Item".format(self.doctype)
				parent_dict.update({"document_type": document_type})

			# party_name field used for customer in quotation
			if self.doctype == "Quotation" and self.quotation_to == "Customer" and parent_dict.get("party_name"):
				parent_dict.update({"customer": parent_dict.get("party_name")})

			self.pricing_rules = []
			for item in self.get("items"):
				if item.get("item_code"):
					args = parent_dict.copy()
					args.update(item.as_dict())

					args["doctype"] = self.doctype
					args["name"] = self.name
					args["child_docname"] = item.name
					args["ignore_pricing_rule"] = self.ignore_pricing_rule if hasattr(self, 'ignore_pricing_rule') else 0

					if not args.get("transaction_date"):
						args["transaction_date"] = args.get("posting_date")

					if self.get("is_subcontracted"):
						args["is_subcontracted"] = self.is_subcontracted

					ret = get_item_details(args, self, for_validate=True, overwrite_warehouse=False)

					for fieldname, value in ret.items():
						if item.meta.get_field(fieldname) and value is not None:
							if (item.get(fieldname) is None or fieldname in force_item_fields):
								item.set(fieldname, value)

							elif fieldname in ['cost_center', 'conversion_factor'] and not item.get(fieldname):
								item.set(fieldname, value)

							elif fieldname == "serial_no":
								# Ensure that serial numbers are matched against Stock UOM
								item_conversion_factor = item.get("conversion_factor") or 1.0
								item_qty = abs(item.get("qty")) * item_conversion_factor

								if item_qty != len(get_serial_nos(item.get('serial_no'))):
									item.set(fieldname, value)

					if self.doctype in ["Purchase Invoice", "Sales Invoice"] and item.meta.get_field('is_fixed_asset'):
						item.set('is_fixed_asset', ret.get('is_fixed_asset', 0))

					# Double check for cost center
					# Items add via promotional scheme may not have cost center set
					if hasattr(item, 'cost_center') and not item.get('cost_center'):
						item.set('cost_center', self.get('cost_center') or erpnext.get_default_cost_center(self.company))

					if ret.get("pricing_rules"):
						self.apply_pricing_rule_on_items(item, ret)
						self.set_pricing_rule_details(item, ret)

			if self.doctype == "Purchase Invoice":
				self.set_expense_account(for_validate)

	def get_party(self):
		party_type = None
		if self.doctype in ("Nanak Pick List","Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
			party_type = 'Customer'

		elif self.doctype in ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"):
			party_type = 'Supplier'

		elif self.meta.get_field("customer"):
			party_type = "Customer"

		elif self.meta.get_field("supplier"):
			party_type = "Supplier"

		party = self.get(party_type.lower()) if party_type else None

		return party_type, party

	def is_internal_transfer(self):
		"""
			It will an internal transfer if its an internal customer and representation
			company is same as billing company
		"""
		if self.doctype in ('Nanak Pick List','Sales Invoice', 'Delivery Note', 'Sales Order'):
			internal_party_field = 'is_internal_customer'
		elif self.doctype in ('Purchase Invoice', 'Purchase Receipt', 'Purchase Order'):
			internal_party_field = 'is_internal_supplier'

		if self.get(internal_party_field) and (self.represents_company == self.company):
			return True

		return False
	
	def calculate_taxes_and_totals(self):
		# nanak_customization\nanak_customization\custom_controllers\taxes_and_totals.py
		from nanak_customization.custom_controllers.taxes_and_totals import calculate_taxes_and_totals
		calculate_taxes_and_totals(self)

		if self.doctype in ["Nanak Pick List","Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			# self.calculate_commission()
			self.calculate_contribution()
	
	# override mrthod from accounts controller

	# ovveride method from selling controllers

	# run onload event of parent and define new function to extend it
	def onload(self):
		super(NanakPickList, self).onload()
		if self.doctype in ("Nanak Pick List"):
			for item in self.get("items"):
				item.update(get_bin_details(item.item_code, item.warehouse))

	# ovveride method from selling controllers

	# ovveride method from stock controllers

	def set_rate_of_stock_uom(self):
		if self.doctype in ['Nanak Pick List',"Purchase Receipt", "Purchase Invoice", "Purchase Order", "Sales Invoice", "Sales Order", "Delivery Note", "Quotation"]:
			for d in self.get("items"):
				d.stock_uom_rate = d.rate / (d.conversion_factor or 1)

	# ovveride method from stock controllers

	# ovveride method from taxes and chargers controllers

	def calculate_item_values(self):
		if not self.discount_amount_applied:
			for item in self.doc.get("items"):
				self.doc.round_floats_in(item)

				if item.discount_percentage == 100:
					item.rate = 0.0
				elif item.price_list_rate:
					if not item.rate or (item.pricing_rules and item.discount_percentage > 0):
						item.rate = flt(item.price_list_rate *
							(1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))
						item.discount_amount = item.price_list_rate * (item.discount_percentage / 100.0)
					elif item.discount_amount and item.pricing_rules:
						item.rate =  item.price_list_rate - item.discount_amount

				if item.doctype in ['Nanak Pick List Item','Nanak Pick List','Quotation Item', 'Sales Order Item', 'Delivery Note Item', 'Sales Invoice Item', 'POS Invoice Item', 'Purchase Invoice Item', 'Purchase Order Item', 'Purchase Receipt Item']:
					item.rate_with_margin, item.base_rate_with_margin = self.calculate_margin(item)
					if flt(item.rate_with_margin) > 0:
						item.rate = flt(item.rate_with_margin * (1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))

						if item.discount_amount and not item.discount_percentage:
							item.rate = item.rate_with_margin - item.discount_amount
						else:
							item.discount_amount = item.rate_with_margin - item.rate

					elif flt(item.price_list_rate) > 0:
						item.discount_amount = item.price_list_rate - item.rate
				elif flt(item.price_list_rate) > 0 and not item.discount_amount:
					item.discount_amount = item.price_list_rate - item.rate

				item.net_rate = item.rate

				if not item.qty and self.doc.get("is_return"):
					item.amount = flt(-1 * item.rate, item.precision("amount"))
				else:
					item.amount = flt(item.rate * item.qty,	item.precision("amount"))

				item.net_amount = item.amount

				self._set_in_company_currency(item, ["price_list_rate", "rate", "net_rate", "amount", "net_amount"])

				item.item_tax_amount = 0.0

	def calculate_totals(self):
		# console(self.doc.get("taxes")).log()
		self.doc.grand_total = flt(self.doc.get("taxes")[-1].total) + flt(self.doc.rounding_adjustment) \
			if self.doc.get("taxes") else flt(self.doc.net_total)

		self.doc.total_taxes_and_charges = flt(self.doc.grand_total - self.doc.net_total
			- flt(self.doc.rounding_adjustment), self.doc.precision("total_taxes_and_charges"))

		self._set_in_company_currency(self.doc, ["total_taxes_and_charges", "rounding_adjustment"])

		if self.doc.doctype in ['Nanak Pick List',"Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice"]:
			self.doc.base_grand_total = flt(self.doc.grand_total * self.doc.conversion_rate, self.doc.precision("base_grand_total")) \
				if self.doc.total_taxes_and_charges else self.doc.base_net_total
		else:
			self.doc.taxes_and_charges_added = self.doc.taxes_and_charges_deducted = 0.0
			for tax in self.doc.get("taxes"):
				# console(tax.category).log()
				if tax.category in ["Valuation and Total", "Total"]:
					if tax.add_deduct_tax == "Add":
						self.doc.taxes_and_charges_added += flt(tax.tax_amount_after_discount_amount)
					else:
						self.doc.taxes_and_charges_deducted += flt(tax.tax_amount_after_discount_amount)

			self.doc.round_floats_in(self.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"])

			self.doc.base_grand_total = flt(self.doc.grand_total * self.doc.conversion_rate) \
				if (self.doc.taxes_and_charges_added or self.doc.taxes_and_charges_deducted) \
				else self.doc.base_net_total

			self._set_in_company_currency(self.doc,
				["taxes_and_charges_added", "taxes_and_charges_deducted"])

		self.doc.round_floats_in(self.doc, ["grand_total", "base_grand_total"])

		self.set_rounded_total()

	# ovveride method from taxes and chargers controllers
	
	
	def before_print(self, settings=None):
		def toggle_print_hide(meta, fieldname):
			df = meta.get_field(fieldname)
			if self.get("print_without_amount"):
				df.set("__print_hide", 1)
			else:
				df.delete_key("__print_hide")

		item_meta = frappe.get_meta("Nanak Pick List Item")
		print_hide_fields = {
			"parent": ["grand_total", "rounded_total", "in_words", "currency", "total", "taxes"],
			"items": ["rate", "amount", "discount_amount", "price_list_rate", "discount_percentage"]
		}

		for key, fieldname in print_hide_fields.items():
			for f in fieldname:
				toggle_print_hide(self.meta if key == "parent" else item_meta, f)

		super(NanakPickList, self).before_print(settings)

	def set_actual_qty(self):
		for d in self.get('items'):
			if d.item_code and d.warehouse:
				actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
					where item_code = %s and warehouse = %s""", (d.item_code, d.warehouse))
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0

	def so_required(self):
		"""check in manage account if sales order required or not"""
		if frappe.db.get_value("Selling Settings", None, 'so_required') == 'Yes':
			for d in self.get('items'):
				if not d.against_sales_order:
					frappe.throw(_("Sales Order required for Item {0}").format(d.item_code))

	def validate(self):

		
		# data = check_credit_limit(self.customer, self.company, True, self.grand_total)
		
		# if data:
		# 	if data[3] == 0:
		# 		if data[2]["customer_group"] < data[0]:
		# 			frappe.throw("Credit limit has been crossed for Customer Group of "+ self.customer +" ("+str(data[0])+"/"+str(data[2]["customer_group"])+")")
		# 		elif data[2]["customer"] < data[1]:
		# 			frappe.throw("Credit limit has been crossed for Customer of "+ self.customer +" ("+str(data[1])+"/"+str(data[2]["customer"])+")")
		
 		
		self.validate_posting_time()
		super(NanakPickList, self).validate()
		self.set_status()
		self.so_required()
		self.validate_proj_cust()
		self.check_sales_order_on_hold_or_close("against_sales_order")
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.validate_with_previous_doc()

		from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
		make_packing_list(self)

		if self._action != 'submit' and not self.is_return:
			set_batch_nos(self, 'warehouse', throw=True)
			set_batch_nos(self, 'warehouse', throw=True, child_table="packed_items")

		self.update_current_stock()

		if not self.installation_status: self.installation_status = 'Not Installed'

	def validate_with_previous_doc(self):
		super(NanakPickList, self).validate_with_previous_doc({
			"Sales Order": {
				"ref_dn_field": "against_sales_order",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Sales Order Item": {
				"ref_dn_field": "so_detail",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Sales Invoice": {
				"ref_dn_field": "against_sales_invoice",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Sales Invoice Item": {
				"ref_dn_field": "si_detail",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
		})

		if cint(frappe.db.get_single_value('Selling Settings', 'maintain_same_sales_rate')) \
				and not self.is_return:
			self.validate_rate_with_reference_doc([["Sales Order", "against_sales_order", "so_detail"],
				["Sales Invoice", "against_sales_invoice", "si_detail"]])

	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			res = frappe.db.sql("""select name from `tabProject`
				where name = %s and (customer = %s or
					ifnull(customer,'')='')""", (self.project, self.customer))
			if not res:
				frappe.throw(_("Customer {0} does not belong to project {1}").format(self.customer, self.project))

	def validate_warehouse(self):
		super(NanakPickList, self).validate_warehouse()

		for d in self.get_item_list():
			if not d['warehouse'] and frappe.db.get_value("Item", d['item_code'], "is_stock_item") == 1:
				frappe.throw(_("Warehouse required for stock Item {0}").format(d["item_code"]))


	def update_current_stock(self):
		if self.get("_action") and self._action != "update_after_submit":
			for d in self.get('items'):
				d.actual_qty = frappe.db.get_value("Bin", {"item_code": d.item_code,
					"warehouse": d.warehouse}, "actual_qty")

			for d in self.get('packed_items'):
				bin_qty = frappe.db.get_value("Bin", {"item_code": d.item_code,
					"warehouse": d.warehouse}, ["actual_qty", "projected_qty"], as_dict=True)
				if bin_qty:
					d.actual_qty = flt(bin_qty.actual_qty)
					d.projected_qty = flt(bin_qty.projected_qty)
	
	def update_picked_qty_in_so(self):
		for item in self.items:
			if item.so_detail:
				qty = frappe.db.sql("""select sum(qty) as qty,item_code from `tabNanak Pick List Item` where so_detail = %(so_name)s and docstatus = 1 group by so_detail""",({"so_name":item.so_detail}),as_dict=1)
				# frappe.throw(str(qty))
				# updated = float(qty[0][0]) + float(item.qty)
				# frappe.msgprint(str(qty))
				# frappe.msgprint(str(updated))
				# frappe.msgprint(str(item.so_detail))
				frappe.db.set_value("Sales Order Item",item.so_detail,"picked_qty",qty[0]['qty'])
		frappe.db.commit()

	def before_submit(self):
		name = frappe.db.get_value("Allow Credit Limit Item", {'customer': self.customer}, "name")
		if name:
			frappe.db.delete("Allow Credit Limit Item", {
				"name": ("=", name)
			})
		else:
			credit_days_data = get_credit_days(self.customer, self.company)

			# frappe.throw(str(credit_days_data[0][0].date) + "/" + str(credit_days_data[1]))
			if credit_days_data:
				if int(credit_days_data['days_from_last_invoice']) > int(credit_days_data['credit_days']):
					if int(credit_days_data['is_group']) == 0:
						frappe.throw("Credit Limit Days Exceeded for Customer - " + self.customer + " (" + str(credit_days_data['days_from_last_invoice']) + "/" + str(credit_days_data['credit_days']) + " Days)")
					else:
						frappe.throw("Credit Limit Days Exceeded for Customer Group - " + credit_days_data['customer_group'] + " (" + str(credit_days_data['days_from_last_invoice']) + "/" + str(credit_days_data['credit_days']) + " Days)")

			credit_limit_data = check_credit_limit(self.customer, self.company, True, self.grand_total)
			if credit_limit_data:
				if int(credit_limit_data['is_group']) == 0:
					frappe.throw("Credit Limit Amount Exceeded for Customer - "+ self.customer + " ("+str(credit_limit_data['customer_outstanding'])+"/"+str(credit_limit_data['credit_limit'])+")")
				else:
					frappe.throw("Credit Limit Amount Exceeded for Customer - "+ credit_limit_data['customer_group'] + " ("+str(credit_limit_data['group_outstanding'])+"/"+str(credit_limit_data['credit_limit'])+")")


		self.update_picked_qty_in_so()
		create_stock_reservation(self)
		

	

	def on_cancel(self):
		super(NanakPickList, self).on_cancel()
		for item in self.items:
			if item.so_detail:
				old_picked = frappe.db.get_value("Sales Order Item",item.so_detail,"picked_qty")
				frappe.db.set_value("Sales Order Item",item.so_detail,"picked_qty",float(old_picked) - float(item.qty))			
				frappe.db.set_value("Nanak Pick List Item",item.name,"dereserved",1)

		# self.check_sales_order_on_hold_or_close("against_sales_order")
		# self.check_next_docstatus()

		# self.update_prevdoc_status()
		# self.update_billing_status()

		# # Updating stock ledger should always be called after updating prevdoc status,
		# # because updating reserved qty in bin depends upon updated delivered qty in SO
		# self.update_stock_ledger()

		# self.cancel_packing_slips()

		# self.make_gl_entries_on_cancel()
		# self.repost_future_sle_and_gle()
		# self.ignore_linked_doctypes = ('GL Entry', 'Stock Ledger Entry', 'Repost Item Valuation')
		# create_stock_reservation(self,cancel=1)

	# def check_credit_limit(self):
	# 	# frappe.msgprint("check credit limit")
	# 	from erpnext.selling.doctype.customer.customer import check_credit_limit

	# 	extra_amount = 0
	# 	validate_against_credit_limit = False
	# 	bypass_credit_limit_check_at_sales_order = cint(frappe.db.get_value("Customer Credit Limit",
	# 		filters={'parent': self.customer, 'parenttype': 'Customer', 'company': self.company},
	# 		fieldname="bypass_credit_limit_check"))

	# 	if bypass_credit_limit_check_at_sales_order:
	# 		validate_against_credit_limit = True
	# 		extra_amount = self.base_grand_total
	# 	else:
	# 		for d in self.get("items"):
	# 			if not (d.against_sales_order or d.against_sales_invoice):
	# 				validate_against_credit_limit = True
	# 				break

	# 	if validate_against_credit_limit:
	# 		check_credit_limit(self.customer, self.company,
	# 			bypass_credit_limit_check_at_sales_order, extra_amount)

	def validate_packed_qty(self):
		"""
			Validate that if packed qty exists, it should be equal to qty
		"""
		if not any(flt(d.get('packed_qty')) for d in self.get("items")):
			return
		has_error = False
		for d in self.get("items"):
			if flt(d.get('qty')) != flt(d.get('packed_qty')):
				frappe.msgprint(_("Packed quantity must equal quantity for Item {0} in row {1}").format(d.item_code, d.idx))
				has_error = True
		if has_error:
			raise frappe.ValidationError

	def check_next_docstatus(self):
		submit_rv = frappe.db.sql("""select t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.delivery_note = %s and t1.docstatus = 1""",
			(self.name))
		if submit_rv:
			frappe.throw(_("Sales Invoice {0} has already been submitted").format(submit_rv[0][0]))

		submit_in = frappe.db.sql("""select t1.name
			from `tabInstallation Note` t1, `tabInstallation Note Item` t2
			where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1""",
			(self.name))
		if submit_in:
			frappe.throw(_("Installation Note {0} has already been submitted").format(submit_in[0][0]))

	def cancel_packing_slips(self):
		"""
			Cancel submitted packing slips related to this Nanak Pick List
		"""
		res = frappe.db.sql("""SELECT name FROM `tabPacking Slip` WHERE delivery_note = %s
			AND docstatus = 1""", self.name)

		if res:
			for r in res:
				ps = frappe.get_doc('Packing Slip', r[0])
				ps.cancel()
			frappe.msgprint(_("Packing Slip(s) cancelled"))

	def update_status(self, status):
		self.set_status(update=True, status=status)
		self.notify_update()
		clear_doctype_notifications(self)

	def update_billing_status(self, update_modified=True):
		updated_delivery_notes = [self.name]
		for d in self.get("items"):
			if d.si_detail and not d.so_detail:
				d.db_set('billed_amt', d.amount, update_modified=update_modified)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			dn_doc = self if (dn == self.name) else frappe.get_doc("Nanak Pick List", dn)
			dn_doc.update_billing_percentage(update_modified=update_modified)

		self.load_from_db()

	def make_return_invoice(self):
		try:
			return_invoice = make_sales_invoice(self.name)
			return_invoice.is_return = True
			return_invoice.save()
			return_invoice.submit()

			credit_note_link = frappe.utils.get_link_to_form('Sales Invoice', return_invoice.name)

			frappe.msgprint(_("Credit Note {0} has been created automatically").format(credit_note_link))
		except:
			frappe.throw(_("Could not create Credit Note automatically, please uncheck 'Issue Credit Note' and submit again"))
	pass

# Credit Control Functionality
@frappe.whitelist()
def check_credit_limit(customer, company, ignore_outstanding_sales_order=True, extra_amount=0):
	dict_credit_limit = {}
	
	name = frappe.db.get_value("Allow Credit Limit Item", {'customer': customer}, "name")
	# frappe.msgprint(str(name))
	if name:
	# 	frappe.db.delete("Allow Credit Limit Item", {
	# 		"name": ("=", name)
	# 	})
		dict_credit_limit["allow_credit"] = 1
	else:
		dict_credit_limit["allow_credit"] = 0
	dict_credit_limit = check_credit_limit_customer(customer, company, ignore_outstanding_sales_order, extra_amount, dict_credit_limit)

	# frappe.msgprint(str(credit_limit))
	if not dict_credit_limit:
		dict_credit_limit = {}
		dict_credit_limit = check_credit_limit_customer_group(customer, company, ignore_outstanding_sales_order, extra_amount, dict_credit_limit)
		if dict_credit_limit:
			dict_credit_limit["is_group"] = 1
			return dict_credit_limit
		else:
			return
	else:
		dict_credit_limit["is_group"] = 0
		return dict_credit_limit

	#02-06-2022 code comment start
	# customers = frappe.db.sql("select name, customer_group from `tabCustomer` where customer_group = (select customer_group from `tabCustomer` where name = %s)", (customer), as_dict = True)
	# group_outstanding = 0
	# for cust in customers:
	# 	group_outs = get_customer_outstanding(cust.name, company, ignore_outstanding_sales_order)
	# 	if group_outs:
	# 		group_outstanding = group_outstanding + group_outs

	# customer_outstanding = get_customer_outstanding(customer, company, ignore_outstanding_sales_order)
	
	# customer_outstanding = flt(customer_outstanding) + flt(extra_amount)
	# group_outstanding = flt(group_outstanding) + flt(extra_amount)
	# # frappe.msgprint(str(customer_outstanding) + ' - ' + extra_amount + ' - ' + str(customer_extra))



	# if credit_limit['customer'] > 0 and (customer_outstanding > credit_limit['customer'] or group_outstanding > credit_limit['customer_group']):
	# 	# frappe.msgprint(_("Credit limit has been crossed for customer {0} ({1}/{2})")
	# 	# 	.format(customer, customer_outstanding, credit_limit))
	# 	allow_credit = frappe.get_value("Allow Credit Limit Item",{"customer": customer},"allow")

	# 	if not allow_credit:
	# 		allow_credit = 0

	# 	return [group_outstanding,customer_outstanding,credit_limit,allow_credit, customers[0].customer_group]
	# else:
	# 	return 0
	#02-06-2022 code comment ends

		# # If not authorized person raise exception
		# credit_controller_role = frappe.db.get_single_value('Accounts Settings', 'credit_controller')
		# if not credit_controller_role or credit_controller_role not in frappe.get_roles():
		# 	# form a list of emails for the credit controller users
		# 	credit_controller_users = get_users_with_role(credit_controller_role or "Sales Master Manager")

		# 	# form a list of emails and names to show to the user
		# 	credit_controller_users_formatted = [get_formatted_email(user).replace("<", "(").replace(">", ")") for user in credit_controller_users]
		# 	if not credit_controller_users_formatted:
		# 		frappe.throw(_("Please contact your administrator to extend the credit limits for {0}.").format(customer))

		# 	message = """Please contact any of the following users to extend the credit limits for {0}:
		# 		<br><br><ul><li>{1}</li></ul>""".format(customer, '<li>'.join(credit_controller_users_formatted))

		# 	# if the current user does not have permissions to override credit limit,
		# 	# prompt them to send out an email to the controller users
		# 	frappe.msgprint(message,
		# 		title="Notify",
		# 		raise_exception=1,
		# 		primary_action={
		# 			'label': 'Send Email',
		# 			'server_action': 'erpnext.selling.doctype.customer.customer.send_emails',
		# 			'args': {
		# 				'customer': customer,
		# 				'customer_outstanding': customer_outstanding,
		# 				'credit_limit': credit_limit,
		# 				'credit_controller_users_list': credit_controller_users
		# 			}
		# 		}
		# 	)

def check_credit_limit_customer(customer, company, ignore_outstanding_sales_order, extra_amount, dict_credit_limit):
	dict_credit_limit = get_credit_limit_customer(customer, company, dict_credit_limit)

	customer_outstanding = get_customer_outstanding(customer, company, ignore_outstanding_sales_order)
	customer_outstanding = flt(customer_outstanding) + flt(extra_amount)

	if dict_credit_limit['credit_limit'] > 0 and customer_outstanding > dict_credit_limit['credit_limit']:
		dict_credit_limit['customer_outstanding'] = customer_outstanding
		return dict_credit_limit


def check_credit_limit_customer_group(customer, company, ignore_outstanding_sales_order, extra_amount, dict_credit_limit):
	dict_credit_limit = get_credit_limit_customer_group(customer, company,dict_credit_limit)

	customers = frappe.db.sql("select name, customer_group from `tabCustomer` where customer_group = (select customer_group from `tabCustomer` where name = %s)", (customer), as_dict = True)
	group_outstanding = 0
	for cust in customers:
		group_outs = get_customer_outstanding(cust.name, company, ignore_outstanding_sales_order)
		if group_outs:
			group_outstanding = group_outstanding + group_outs

	group_outstanding = flt(group_outstanding) + flt(extra_amount)

	if dict_credit_limit['credit_limit'] > 0 and group_outstanding > dict_credit_limit['credit_limit']:
		dict_credit_limit['group_outstanding'] = group_outstanding
		dict_credit_limit['customer_group'] = customers[0].customer_group
		return dict_credit_limit


# def get_credit_limit(customer, company):

# 	if customer:
# 		credit_limit = get_credit_limit_customer(customer, company)

# 		if not credit_limit:
# 			credit_limit = get_credit_limit_customer_group(customer, company)

# 	# if not credit_limit.customer:
# 	# 	credit_limit.customer = 0

# 	# if not credit_limit.customer_group:
# 	# 	credit_limit.customer_group = 0

# 	return credit_limit

def get_credit_limit_customer(customer, company, dict_credit_limit):
	credit_limit = flt(frappe.db.get_value("Customer",
	customer, 'credit_amount'))
	
	dict_credit_limit["credit_limit"] = credit_limit
	return dict_credit_limit

def get_credit_limit_customer_group(customer, company, dict_credit_limit):
	customer_group = frappe.get_cached_value("Customer", customer, 'customer_group')
	credit_limit = flt(frappe.db.get_value("Customer Group",
		customer_group, 'credit_amount'))

	dict_credit_limit["credit_limit"] = credit_limit
	return dict_credit_limit

@frappe.whitelist()
def get_credit_days(customer, company,date=None):
	dict_credit_days = {}
	if date:
		name = frappe.db.get_value("Allow Credit Limit Item", {'customer': customer}, "name")
		if name:
			return
	# 	frappe.db.delete("Allow Credit Limit Item", {
	# 		"name": ("=", name)
	# 	})
	# 	dict_credit_days["allow_credit"] = 1
	# else:
	# 	dict_credit_days["allow_credit"] = 0


	
	dict_credit_days = check_credit_days_customer(customer, company, dict_credit_days)
	
	if not dict_credit_days:
		dict_credit_days = {}
		dict_credit_days = check_credit_days_customer_group(customer, company, dict_credit_days)
		if dict_credit_days:
			dict_credit_days["is_group"] = 1
			return dict_credit_days
		else:
			return
	else:
		dict_credit_days["is_group"] = 0
		return dict_credit_days

	# from frappe.utils import add_days
	# customer_group = frappe.get_cached_value("Customer", customer, 'customer_group')
	# credit_days_customer_group = frappe.db.get_value("Customer Credit Limit",
	# 	{'parent': customer_group, 'parenttype': 'Customer Group', 'company': company}, 'credit_days')

	# credit_days_customer = frappe.db.get_value("Customer Credit Limit",
	# 	{'parent': customer, 'parenttype': 'Customer', 'company': company}, 'credit_days')

	# # frappe.msgprint(str(credit_days_customer_group))
	# # frappe.msgprint(str(credit_days_customer))
	
	
	# if credit_days_customer or credit_days_customer_group:
	
	# 	credit_day = credit_days_customer_group if int(credit_days_customer_group)<int(credit_days_customer) else credit_days_customer
	# 	# frappe.msgprint(str(credit_day))
	# 	if credit_day:

	# 		# last_date = add_days(date, -(credit_day))
	# 		# frappe.msgprint(str(last_date))
	# 		# days_from_last_invoice_raw_test = frappe.db.sql("select DATEDIFF(CURDATE(),si.posting_date) as date,name from `tabSales Invoice` si where si.customer = %s and si.outstanding_amount > 0 order by si.posting_date asc limit 1 ", (customer), as_dict =1)
	# 		# frappe.msgprint(str(days_from_last_invoice_raw_test))

	# 		customer_group = ""

	# 		days_from_last_invoice_raw = frappe.db.sql("select DATEDIFF(CURDATE(),si.posting_date) as date, si.customer, c.customer_group from `tabSales Invoice` si left join `tabCustomer` c on c.name = si.customer where si.customer in (select c1.name from `tabCustomer` c1 where c1.customer_group = (select c2.customer_group from `tabCustomer` c2 where c2.name = %s)) and si.outstanding_amount > 0 order by si.posting_date asc limit 1", (customer), as_dict =1)
	# 		if not days_from_last_invoice_raw:
	# 			days_from_last_invoice = 0
	# 		else:
	# 			days_from_last_invoice = str(days_from_last_invoice_raw[0].date)
	# 			if customer != days_from_last_invoice_raw[0].customer:
	# 				customer_group = days_from_last_invoice_raw[0].customer_group

			

	# 		# pending_invoices = frappe.db.sql("""
	# 		# select si.name as invoice from `tabSales Invoice` si where si.posting_date < %s and si.customer = %s and si.outstanding_amount > 0
	# 		# """,(last_date,customer),as_dict = 1)
	# 		# pending_str = [i['invoice'] for i in pending_invoices]
			
	# 		# frappe.msgprint(str(customer))
	# 		# out_standing_amount = frappe.db.sql("""
	# 		# select si.outstanding_amount,si.name from `tabSales Invoice` si where si.posting_date < %s and si.customer = %s and si.outstanding_amount > 0 and si.docstatus = 1
	# 		# """,(last_date,customer),as_dict = 1)
	# 		# frappe.msgprint(str(out_standing_amount))

	# 		# if out_standing_amount[0]['outstand'] > 0:
	# 		# 	frappe.msgprint("Customer Has Outstanding Amount of {} according to credit days".format(out_standing_amount[0]['outstand']))

	# 		return {
	# 			# "count" : len(pending_invoices),
	# 			# "invoices":pending_invoices,
	# 			# "pending_str":str(pending_str),
	# 			"pending_invoice_date": str(days_from_last_invoice),
	# 			"customer_credit_days": str(credit_day),
	# 			"customer_group": customer_group
	# 		}
		
def check_credit_days_customer(customer, company, dict_credit_days):
	credit_days = frappe.db.get_value("Customer",
		customer, 'credit_days')

	if credit_days:
		days_from_last_invoice_raw = frappe.db.sql("select DATEDIFF(CURDATE(),si.posting_date) as date from `tabSales Invoice` si where si.customer = %s and si.outstanding_amount > 0 order by si.posting_date asc limit 1", (customer), as_dict = True)

		if days_from_last_invoice_raw:
			if days_from_last_invoice_raw[0].date > credit_days:
				dict_credit_days["days_from_last_invoice"] = days_from_last_invoice_raw[0].date
				dict_credit_days["credit_days"] = credit_days	
				return dict_credit_days
			
		return

def check_credit_days_customer_group(customer, company, dict_credit_days):
	customer_group = frappe.get_cached_value("Customer", customer, 'customer_group')
	credit_days = frappe.db.get_value("Customer Group",
		customer_group, 'credit_days')

	if credit_days:
		days_from_last_invoice_raw = frappe.db.sql("select DATEDIFF(CURDATE(),si.posting_date) as date, c.customer_group from `tabSales Invoice` si left join `tabCustomer` c on c.name = si.customer where si.customer in (select c1.name from `tabCustomer` c1 where c1.customer_group = (select c2.customer_group from `tabCustomer` c2 where c2.name = %s)) and si.outstanding_amount > 0 order by si.posting_date asc limit 1", (customer), as_dict =1)

		if days_from_last_invoice_raw:
			if days_from_last_invoice_raw[0].date > credit_days:
				dict_credit_days["days_from_last_invoice"] = days_from_last_invoice_raw[0].date
				dict_credit_days["customer_group"] = days_from_last_invoice_raw[0].customer_group
				dict_credit_days["credit_days"] = credit_days	
				return dict_credit_days
			
		return

# def get_credit_limit(customer, company):
# 	credit_limit = None

# 	if customer:
# 		credit_limit = frappe.db.get_value("Customer Credit Limit",
# 			{'parent': customer, 'parenttype': 'Customer', 'company': company}, 'credit_limit')

# 		if not credit_limit:
# 			customer_group = frappe.get_cached_value("Customer", customer, 'customer_group')
# 			credit_limit = frappe.db.get_value("Customer Credit Limit",
# 				{'parent': customer_group, 'parenttype': 'Customer Group', 'company': company}, 'credit_limit')

# 	if not credit_limit:
# 		credit_limit = frappe.get_cached_value('Company',  company,  "credit_limit")

# 	return flt(credit_limit)
			

	

def get_customer_outstanding(customer, company, ignore_outstanding_sales_order=False, cost_center=None):
	# Outstanding based on GL Entries

	cond = ""
	if cost_center:
		lft, rgt = frappe.get_cached_value("Cost Center",
			cost_center, ['lft', 'rgt'])

		cond = """ and cost_center in (select name from `tabCost Center` where
			lft >= {0} and rgt <= {1})""".format(lft, rgt)

	outstanding_based_on_gle = frappe.db.sql("""
		select sum(debit) - sum(credit)
		from `tabGL Entry` where party_type = 'Customer'
		and party = %s and company=%s {0}""".format(cond), (customer, company))

	outstanding_based_on_gle = flt(outstanding_based_on_gle[0][0]) if outstanding_based_on_gle else 0

	# Outstanding based on Sales Order
	outstanding_based_on_so = 0

	# if credit limit check is bypassed at sales order level,
	# we should not consider outstanding Sales Orders, when customer credit balance report is run
	if not ignore_outstanding_sales_order:
		outstanding_based_on_so = frappe.db.sql("""
			select sum(base_grand_total*(100 - per_billed)/100)
			from `tabSales Order`
			where customer=%s and docstatus = 1 and company=%s
			and per_billed < 100 and status != 'Closed'""", (customer, company))

		outstanding_based_on_so = flt(outstanding_based_on_so[0][0]) if outstanding_based_on_so else 0

	# Outstanding based on Delivery Note, which are not created against Sales Order
	outstanding_based_on_dn = 0

	unmarked_delivery_note_items = frappe.db.sql("""select
			dn_item.name, dn_item.amount, dn.base_net_total, dn.base_grand_total
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where
			dn.name = dn_item.parent
			and dn.customer=%s and dn.company=%s
			and dn.docstatus = 1 and dn.status not in ('Closed', 'Stopped')
			and ifnull(dn_item.against_sales_order, '') = ''
			and ifnull(dn_item.against_sales_invoice, '') = ''
		""", (customer, company), as_dict=True)

	if not unmarked_delivery_note_items:
		return outstanding_based_on_gle + outstanding_based_on_so

	si_amounts = frappe.db.sql("""
		SELECT
			dn_detail, sum(amount) from `tabSales Invoice Item`
		WHERE
			docstatus = 1
			and dn_detail in ({})
		GROUP BY dn_detail""".format(", ".join(
			frappe.db.escape(dn_item.name)
			for dn_item in unmarked_delivery_note_items
		))
	)

	si_amounts = {si_item[0]: si_item[1] for si_item in si_amounts}

	for dn_item in unmarked_delivery_note_items:
		dn_amount = flt(dn_item.amount)
		si_amount = flt(si_amounts.get(dn_item.name))

		if dn_amount > si_amount and dn_item.base_net_total:
			outstanding_based_on_dn += ((dn_amount - si_amount)
				/ dn_item.base_net_total) * dn_item.base_grand_total

	return outstanding_based_on_gle + outstanding_based_on_so + outstanding_based_on_dn

# Credit Control Functionality

def update_billed_amount_based_on_so(so_detail, update_modified=True):
	# Billed against Sales Order directly
	billed_against_so = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
		where so_detail=%s and (dn_detail is null or dn_detail = '') and docstatus=1""", so_detail)
	billed_against_so = billed_against_so and billed_against_so[0][0] or 0

	# Get all Nanak Pick List Item rows against the Sales Order Item row
	dn_details = frappe.db.sql("""select dn_item.name, dn_item.amount, dn_item.si_detail, dn_item.parent
		from `tabNanak Pick List Item` dn_item, `tabNanak Pick List` dn
		where dn.name=dn_item.parent and dn_item.so_detail=%s
			and dn.docstatus=1 and dn.is_return = 0
		order by dn.posting_date asc, dn.posting_time asc, dn.name asc""", so_detail, as_dict=1)

	updated_dn = []
	for dnd in dn_details:
		billed_amt_agianst_dn = 0

		# If delivered against Sales Invoice
		if dnd.si_detail:
			billed_amt_agianst_dn = flt(dnd.amount)
			billed_against_so -= billed_amt_agianst_dn
		else:
			# Get billed amount directly against Nanak Pick List
			billed_amt_agianst_dn = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
				where dn_detail=%s and docstatus=1""", dnd.name)
			billed_amt_agianst_dn = billed_amt_agianst_dn and billed_amt_agianst_dn[0][0] or 0

		# Distribute billed amount directly against SO between DNs based on FIFO
		if billed_against_so and billed_amt_agianst_dn < dnd.amount:
			pending_to_bill = flt(dnd.amount) - billed_amt_agianst_dn
			if pending_to_bill <= billed_against_so:
				billed_amt_agianst_dn += pending_to_bill
				billed_against_so -= pending_to_bill
			else:
				billed_amt_agianst_dn += billed_against_so
				billed_against_so = 0

		frappe.db.set_value("Nanak Pick List Item", dnd.name, "billed_amt", billed_amt_agianst_dn, update_modified=update_modified)

		updated_dn.append(dnd.parent)

	return updated_dn

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Shipments'),
	})
	return list_context

def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""", delivery_note):
			if not invoiced_qty_map.get(dn_detail):
				invoiced_qty_map[dn_detail] = 0
			invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map

def get_returned_qty_map(delivery_note):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(frappe.db.sql("""select dn_item.dn_detail, abs(dn_item.qty) as qty
		from `tabNanak Pick List Item` dn_item, `tabNanak Pick List` dn
		where dn.name = dn_item.parent
			and dn.docstatus = 1
			and dn.is_return = 1
			and dn.return_against = %s
	""", delivery_note))

	return returned_qty_map

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	doc = frappe.get_doc('Nanak Pick List', source_name)

	to_make_invoice_qty_map = {}
	# returned_qty_map = get_returned_qty_map(source_name)
	# invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		
		gstin = frappe.db.get_value("Address",source.customer_address,"gstin")
		if gstin:
			target.gst_category = "Registered Regular"
		else:
			target.gst_category = "Unregistered"
		target.po_no = source.po_no
		target.update_stock = 1
		target.set_warehouse = frappe.db.get_value("Nanak Warehouse Table",{"warehouse":source.set_warehouse},"reserve_warehouse")
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been Invoiced/Returned"))

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

	def update_item(source_doc, target_doc, source_parent):
		# target_doc.qty = to_make_invoice_qty_map[source_doc.name]
		target_doc.warehouse = source_parent.set_warehouse
		

		if source_doc.serial_no and source_parent.per_billed > 0 and not source_parent.is_return:
			target_doc.serial_no = get_delivery_note_serial_no(source_doc.item_code,
				target_doc.qty, source_parent.name)

	# def get_pending_qty(item_row):
	# 	pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

	# 	returned_qty = 0
	# 	if returned_qty_map.get(item_row.name, 0) > 0:
	# 		returned_qty = flt(returned_qty_map.get(item_row.name, 0))
	# 		returned_qty_map[item_row.name] -= pending_qty

	# 	if returned_qty:
	# 		if returned_qty >= pending_qty:
	# 			pending_qty = 0
	# 			returned_qty -= pending_qty
	# 		else:
	# 			pending_qty -= returned_qty
	# 			returned_qty = 0

	# 	to_make_invoice_qty_map[item_row.name] = pending_qty

	# 	return pending_qty

	doc = get_mapped_doc("Nanak Pick List", source_name, {
		"Nanak Pick List": {
			"doctype": "Sales Invoice",
			"field_map": {
				"is_return": "is_return",
				"po_no":"po_no"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Nanak Pick List Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "pick_list_details",
				"parent": "nanak_pick_list",
				"so_detail": "so_detail",
				"against_sales_order": "sales_order",
				"serial_no": "serial_no",
				"cost_center": "cost_center"
			},
			"field_no_map":["warehouse"],
			"postprocess": update_item
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		# "Nanak Pick List Payments": {
		# 	"doctype": "Sales Invoice Payment",
		# 	"amount":"amount"
		# },
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doc

@frappe.whitelist()
def make_delivery_trip(source_name, target_doc=None):
	def update_stop_details(source_doc, target_doc, source_parent):
		target_doc.customer = source_parent.customer
		target_doc.address = source_parent.shipping_address_name
		target_doc.customer_address = source_parent.shipping_address
		target_doc.contact = source_parent.contact_person
		target_doc.customer_contact = source_parent.contact_display
		target_doc.grand_total = source_parent.grand_total

		# Append unique Nanak Pick Lists in Delivery Trip
		delivery_notes.append(target_doc.delivery_note)

	delivery_notes = []

	doclist = get_mapped_doc("Nanak Pick List", source_name, {
		"Nanak Pick List": {
			"doctype": "Delivery Trip",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Nanak Pick List Item": {
			"doctype": "Delivery Stop",
			"field_map": {
				"parent": "delivery_note"
			},
			"condition": lambda item: item.parent not in delivery_notes,
			"postprocess": update_stop_details
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_installation_note(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.installed_qty)
		target.serial_no = obj.serial_no

	doclist = get_mapped_doc("Nanak Pick List", source_name, 	{
		"Nanak Pick List": {
			"doctype": "Installation Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Nanak Pick List Item": {
			"doctype": "Installation Note Item",
			"field_map": {
				"name": "prevdoc_detail_docname",
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype",
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.installed_qty < doc.qty
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_packing_slip(source_name, target_doc=None):
	doclist = get_mapped_doc("Nanak Pick List", source_name, 	{
		"Nanak Pick List": {
			"doctype": "Packing Slip",
			"field_map": {
				"name": "delivery_note",
				"letter_head": "letter_head"
			},
			"validation": {
				"docstatus": ["=", 0]
			}
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_shipment(source_name, target_doc=None):
	def postprocess(source, target):
		user = frappe.db.get_value("User", frappe.session.user, ['email', 'full_name', 'phone', 'mobile_no'], as_dict=1)
		target.pickup_contact_email = user.email
		pickup_contact_display = '{}'.format(user.full_name)
		if user:
			if user.email:
				pickup_contact_display += '<br>' + user.email
			if user.phone:
				pickup_contact_display += '<br>' + user.phone
			if user.mobile_no and not user.phone:
				pickup_contact_display += '<br>' + user.mobile_no
		target.pickup_contact = pickup_contact_display

		# As we are using session user details in the pickup_contact then pickup_contact_person will be session user
		target.pickup_contact_person = frappe.session.user

		contact = frappe.db.get_value("Contact", source.contact_person, ['email_id', 'phone', 'mobile_no'], as_dict=1)
		delivery_contact_display = '{}'.format(source.contact_display)
		if contact:
			if contact.email_id:
				delivery_contact_display += '<br>' + contact.email_id
			if contact.phone:
				delivery_contact_display += '<br>' + contact.phone
			if contact.mobile_no and not contact.phone:
				delivery_contact_display += '<br>' + contact.mobile_no
		target.delivery_contact = delivery_contact_display

		if source.shipping_address_name:
			target.delivery_address_name = source.shipping_address_name
			target.delivery_address = source.shipping_address
		elif source.customer_address:
			target.delivery_address_name = source.customer_address
			target.delivery_address = source.address_display

	doclist = get_mapped_doc("Nanak Pick List", source_name, 	{
		"Nanak Pick List": {
			"doctype": "Shipment",
			"field_map": {
				"grand_total": "value_of_goods",
				"company": "pickup_company",
				"company_address": "pickup_address_name",
				"company_address_display": "pickup_address",
				"customer": "delivery_customer",
				"contact_person": "delivery_contact_name",
				"contact_email": "delivery_contact_email"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Nanak Pick List Item": {
			"doctype": "Shipment Nanak Pick List",
			"field_map": {
				"name": "prevdoc_detail_docname",
				"parent": "prevdoc_docname",
				"parenttype": "prevdoc_doctype",
				"base_amount": "grand_total"
			}
		}
	}, target_doc, postprocess)

	return doclist

@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Nanak Pick List", source_name, target_doc)


@frappe.whitelist()
def update_delivery_note_status(docname, status):
	dn = frappe.get_doc("Nanak Pick List", docname)
	dn.update_status(status)

@frappe.whitelist()
def make_inter_company_purchase_receipt(source_name, target_doc=None):
	return make_inter_company_transaction("Nanak Pick List", source_name, target_doc)

def make_inter_company_transaction(doctype, source_name, target_doc=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import (validate_inter_company_transaction,
		get_inter_company_details, update_address, update_taxes, set_purchase_references)

	if doctype == 'Nanak Pick List':
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Receipt"
		source_document_warehouse_field = 'target_warehouse'
		target_document_warehouse_field = 'from_warehouse'
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = 'Nanak Pick List'
		source_document_warehouse_field = 'from_warehouse'
		target_document_warehouse_field = 'target_warehouse'

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

		if target.doctype == 'Purchase Receipt':
			master_doctype = 'Purchase Taxes and Charges Template'
		else:
			master_doctype = 'Sales Taxes and Charges Template'

		if not target.get('taxes') and target.get('taxes_and_charges'):
			for tax in get_taxes_and_charges(master_doctype, target.get('taxes_and_charges')):
				target.append('taxes', tax)

	def update_details(source_doc, target_doc, source_parent):
		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype == 'Purchase Receipt':
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.buying_price_list = source_doc.selling_price_list
			target_doc.is_internal_supplier = 1
			target_doc.inter_company_reference = source_doc.name

			# Invert the address on target doc creation
			update_address(target_doc, 'supplier_address', 'address_display', source_doc.company_address)
			update_address(target_doc, 'shipping_address', 'shipping_address_display', source_doc.customer_address)

			update_taxes(target_doc, party=target_doc.supplier, party_type='Supplier', company=target_doc.company,
				doctype=target_doc.doctype, party_address=target_doc.supplier_address,
				company_address=target_doc.shipping_address)
		else:
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.company_address = source_doc.supplier_address
			target_doc.selling_price_list = source_doc.buying_price_list
			target_doc.is_internal_customer = 1
			target_doc.inter_company_reference = source_doc.name

			# Invert the address on target doc creation
			update_address(target_doc, 'company_address', 'company_address_display', source_doc.supplier_address)
			update_address(target_doc, 'shipping_address_name', 'shipping_address', source_doc.shipping_address)
			update_address(target_doc, 'customer_address', 'address_display', source_doc.shipping_address)

			update_taxes(target_doc, party=target_doc.customer, party_type='Customer', company=target_doc.company,
				doctype=target_doc.doctype, party_address=target_doc.customer_address,
				company_address=target_doc.company_address, shipping_address_name=target_doc.shipping_address_name)

	doclist = get_mapped_doc(doctype, source_name, {
		doctype: {
			"doctype": target_doctype,
			"postprocess": update_details,
			"field_no_map": [
				"taxes_and_charges",
				"set_warehouse"
			]
		},
		doctype +" Item": {
			"doctype": target_doctype + " Item",
			"field_map": {
				source_document_warehouse_field: target_document_warehouse_field,
				'name': 'delivery_note_item',
				'batch_no': 'batch_no',
				'serial_no': 'serial_no'
			},
			"field_no_map": [
				"warehouse"
			]
		}

	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def make_pick_list(source_name, target_doc=None, skip_item_mapping=False):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Nanak Pick List", 'company_address', target.company_address))

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.picked_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.picked_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.picked_qty)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center") \
				or item.get("buying_cost_center") \
				or item_group.get("buying_cost_center")

	mapper = {
		"Sales Order": {
			"doctype": "Nanak Pick List",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}

	if not skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Nanak Pick List Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		}

	target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)

	return target_doc
@frappe.whitelist()
def dereserve_stock(item_reference,so_detail=None,curr_qty=None):
	stock_entry_doc = frappe.get_doc("Stock Entry",{"picklist_item_reference":item_reference,"docstatus":1})
	
	if stock_entry_doc:
		stock_entry_doc.cancel()
		if so_detail:
			old_picked = frappe.db.get_value("Sales Order Item",so_detail,"picked_qty")
			frappe.db.set_value("Sales Order Item",so_detail,"picked_qty",float(old_picked) - float(curr_qty))

		
		
		# frappe.db.set_value("Nanak Pick List Item",item_reference,"dereserved",1)
		return 1
def create_stock_reservation(doc):
	reservation_warehouse = frappe.db.get_value("Nanak Warehouse Table",{"warehouse":doc.set_warehouse},"reserve_warehouse")
	if not reservation_warehouse:
		frappe.throw("Please Set Reservation Warehouse for <b>{}</b> in <b>Nanak Standard Settings!</b>".format(doc.set_warehouse))
	# picked_items= []
	# for item in doc.items:
		
	# 	picked_items.append({
	# 		"s_warehouse":item.warehouse,
	# 		"t_warehouse":reservation_warehouse,
	# 		"item_code":item.item_code,
	# 		"qty":item.picked_quantity,
	# 		"uom":item.uom,
	# 		"conversion_factor":item.conversion_factor,
	# 		"serial_no":item.serial_no,
	# 		"batch_no":item.batch_no,
	# 		"basic_rate":item.rate
	# 	})
	# console(picked_items).log()
	try:
		for item in doc.items:
			reservation_entry = frappe.get_doc({
				"doctype":"Stock Entry",
				"stock_entry_type":"Stock Reservation",
				"nanak_pick_list":doc.name,
				"picklist_item_reference":item.name,
				"items":[{
					"s_warehouse":item.warehouse,
					"t_warehouse":reservation_warehouse,
					"item_code":item.item_code,
					"qty":item.qty,
					"uom":item.uom,
					"conversion_factor":item.conversion_factor,
					"serial_no":item.serial_no,
					"batch_no":item.batch_no,
					"basic_rate":item.rate
				}]
			})
			res=reservation_entry.insert(ignore_permissions=True)
			res.submit()
	except Exception as e:
		
		frappe.throw(str(e))

@frappe.whitelist()
def check_item_stock(item,set_warehouse=None):
	warehouse_stock = []
	if set_warehouse:
		item_stock = get_stock_balance(item,set_warehouse)
		if item_stock > 0:
			return 1
		else:
			warehouse_list = frappe.db.get_list("Warehouse",{"is_group":0,"is_reserve_warehouse":0,"name":["!=",set_warehouse]},["name"])
			
			for warehouse in warehouse_list:
				item_stock = get_stock_balance(item,warehouse['name'])
				if float(item_stock) > 0:
					stock = {
						"warehouse": str(warehouse['name']),
						"stock": float(item_stock)
					}
					warehouse_stock.append(stock)
			
			return warehouse_stock
	else:
		warehouse_list = frappe.db.get_list("Warehouse",{"is_group":0,"is_reserve_warehouse":0},["name"])

		for warehouse in warehouse_list:
			item_stock = get_stock_balance(item,warehouse['name'])

			if float(item_stock) > 0:
				stock = {
					"warehouse": str(warehouse['name']),
					"stock": float(item_stock)
				}
				warehouse_stock.append(stock)

		return warehouse_stock

	#------------------code by Raj ---------------------------------------
	# if set_warehouse:
	# 	item_stock = get_stock_balance(item,set_warehouse)
	# 	if item_stock > 0:
	# 		return 1
	# 	else:
	# 		warehouse_list = frappe.db.get_list("Warehouse",{"is_group":0,"is_reserve_warehouse":0,"name":["!=",set_warehouse]},["name"])
	# 		# items_stock_list = []
	# 		table = """<h3>Item is not Available in selected Warehouse, You can pick it from below options!</h3><table class="table"><tr>
	# 		<th>Warehouse</th>
	# 		<th>Warehouse Qty</th>
					
	# 		</tr>"""
	# 		for warehouse in warehouse_list:
	# 			item_stock = get_stock_balance(item,warehouse['name'])
				
	# 			if float(item_stock) > 0:
	# 				# items_stock_list.append({
	# 				# 	"warehouse":warehouse['name'],
	# 				# 	"qty":item_stock
	# 				# })
			
	# 				table = table + """<tr>
	# 				<td>{0}</td>
	# 				<td>{1}</td>
	# 				</tr>""".format(str(warehouse['name']),str(item_stock))
					

	# 		table = table + """</table>"""
	# 		frappe.throw(table)
	# 		return 0

	# else:
	# 	warehouse_list = frappe.db.get_list("Warehouse",{"is_group":0,"is_reserve_warehouse":0},["name"])
		
	# 	# items_stock_list = []
	# 	table = """<table class="table"><tr>
				
	# 			<th>Warehouse</th>
	# 			<th>Warehouse Qty</th>
	# 			<th>Action</th>
				
	# 			</tr>"""
	# 	for warehouse in warehouse_list:
	# 		item_stock = get_stock_balance(item,warehouse['name'])
			
	# 		if float(item_stock) > 0:
	# 		# 	items_stock_list.append({
	# 		# 		"warehouse":warehouse['name'],
	# 		# 		"qty":item_stock
	# 		# 	})
			
	
	# 			table = table + """<tr>
	# 			<td>{0}</td>
	# 			<td>{1}</td>
	# 			<td><button class="btn btn-xs btn-secondary grid-add-row add-warehouse btn-modal-close " data="{0}">Select</button></td>
				
	# 			</tr>""".format(str(warehouse['name']),str(item_stock))
			

	# 	table = table + """</table>"""
	# 	frappe.throw(table)
		#------------------------Code by Raj------------------------------

@frappe.whitelist()
def check_item_stock_bs(item,set_warehouse=None):
	warehouse_stock = []
	if set_warehouse:
		item_stock = get_stock_balance(item,set_warehouse)
		if item_stock == 0:
			warehouse_list = frappe.db.get_list("Warehouse",{"is_group":0,"is_reserve_warehouse":0,"name":["!=",set_warehouse]},["name"])

			for warehouse in warehouse_list:
				item_stock = get_stock_balance(item,warehouse['name'])

				if float(item_stock) > 0:
					stock = {
					"warehouse": str(warehouse['name']),
					"stock": float(item_stock)
					}
					warehouse_stock.append(stock)
				
			return warehouse_stock

	return 0
	
	#------------------------Code by Raj------------------------------
	# if set_warehouse:
	# 	item_stock = get_stock_balance(item,set_warehouse)
	# 	# frappe.msgprint(str(item_stock))
	# 	if item_stock == 0:
			
	# 		warehouse_list = frappe.db.get_list("Warehouse",{"is_group":0,"is_reserve_warehouse":0,"name":["!=",set_warehouse]},["name"])
	# 		# items_stock_list = []
	# 		table = """<h3>Item is not Available in selected Warehouse, You can pick it from below options!</h3><table class="table"><tr>
	# 		<th>Warehouse</th>
	# 		<th>Warehouse Qty</th>					
	# 		</tr>"""
	# 		for warehouse in warehouse_list:
	# 			item_stock = get_stock_balance(item,warehouse['name'])
				
	# 			if float(item_stock) > 0:
	# 				# items_stock_list.append({
	# 				# 	"warehouse":warehouse['name'],
	# 				# 	"qty":item_stock
	# 				# })
			
	# 				table = table + """<tr>
	# 				<td>{0}</td>
	# 				<td>{1}</td>
					
					
	# 				</tr>""".format(str(warehouse['name']),str(item_stock))
					

	# 		table = table + """</table>"""
	# 		frappe.msgprint(table)
	# 		return 0
	#------------------------Code by Raj------------------------------
			

@frappe.whitelist()
def get_discount(item, customer):
	doc = frappe.db.sql("select discount_percentage from `tabSales Invoice Item` sio left join `tabSales Invoice` si on si.name = sio.parent where si.customer = %s and sio.item_code = %s order by si.creation desc limit 1", (customer, item))
	if doc:
		return doc[0][0]

	




