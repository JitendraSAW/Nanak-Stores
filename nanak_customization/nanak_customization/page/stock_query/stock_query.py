# Copyright (c) 2022, Akhilam and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.batch.batch import get_batch_no,get_batches
# from console import console

class QueryTesting(Document):
	pass
	

@frappe.whitelist()
def get_header_data(item_code):
		# item_code = 'Glass'

		pricelist = frappe.db.get_single_value("Nanak Standard Settings", "stock_query_pricelist")

		data = frappe.db.sql("""
			select
			i.item_name,
			i.item_group,i.stock_category,i.company_code,it.item_tax_template,i.stock_uom,
			(select ip.price_list_rate from `tabItem Price` ip where ip.item_code = i.name and price_list = %s order by creation desc limit 1) as price,
			i.gst_hsn_code,
			(select sum(sle.actual_qty) from `tabBin` sle where sle.item_code = i.name and sle.warehouse in (select W.name from `tabWarehouse` W where W.is_reserve_warehouse = 0) group by sle.item_code) as qty
			from
			`tabItem` i left join `tabItem Tax` it on i.name = it.parent
			where
			i.name = %s
			order by it.valid_from desc
		""", (pricelist,item_code), as_dict = True)

		return data

@frappe.whitelist()
def get_same_category(product_id):
		# product_id = 'Mouse'
		# if want to omit product mouse
		ext = " and i.name != '" + product_id + "'"

		product_group = frappe.db.get_value('Item', product_id, 'stock_category')

		data = frappe.db.sql("""
			select
			i.name,
			i.item_name,
			i.item_group,
			(select sum(sle.actual_qty) from `tabBin` sle where sle.item_code = i.name and sle.warehouse in (select W.name from `tabWarehouse` W where W.is_reserve_warehouse = 0) group by sle.item_code) as qty
			from
			`tabItem` i
			where
			i.stock_category = '%s'
			%s
			
		"""% (product_group, ext), as_dict = True)

		return data

@frappe.whitelist()
def get_godown_wise(product_id):
	# frappe.msgprint("fetch warehouse data")
	warehouse_data = []
	sn_bn = frappe.db.get_value("Item",product_id,["has_serial_no","has_batch_no"],as_dict=1)

	if sn_bn['has_serial_no']:
		actual_data = frappe.db.sql("""
		select wh.is_reserve_warehouse,wh.warehouse as og_warehouse,sn.serial_no,wh.name as warehouse from  `tabWarehouse` wh inner join `tabSerial No` sn on wh.name = sn.warehouse where sn.item_code = %s and sn.status = 'Active'
		""",product_id,as_dict = 1)
		for item in actual_data:
			if item.is_reserve_warehouse:
				warehouse_data.append({
					"warehouse":item.og_warehouse,
					"qty":0,
					"serial_no":item.serial_no,
					"reserved":1
				})
			else:
				warehouse_data.append({
					"warehouse":item.warehouse,
					"qty":1,
					"serial_no":item.serial_no,
					"reserved":0
				})
		return warehouse_data,sn_bn
	if sn_bn['has_batch_no']:
		actual_data = frappe.db.sql("""
		select bn.warehouse,bn.actual_qty,bn.item_code,wh.is_reserve_warehouse,wh.warehouse as og_warehouse from `tabBin` bn inner join `tabWarehouse` wh on wh.name = bn.warehouse where bn.actual_qty > 0 and bn.item_code = %s
		""",product_id,as_dict = 1)
		# console(actual_data).log()
		raw_batch_data = []
		warehouse_data = []
		for item in actual_data:
			batch = get_batches(item.item_code, item.warehouse)
			for b in batch:
				b['warehouse'] = item.warehouse	
				b['is_reserve_warehouse'] = item.is_reserve_warehouse
				b['og_warehouse'] = item.og_warehouse
				raw_batch_data.append(b)
		for item in raw_batch_data:
			if item.is_reserve_warehouse:
				# console(item).log()
				
				
				if any(d['warehouse'] == item.og_warehouse and d['batch_id'] == item.batch_id for d in warehouse_data):
					# console("modify reserve").log()
					
					for data in warehouse_data:
						if data['warehouse'] == item.og_warehouse and data['batch_id'] == item.batch_id:
							data['reserved'] = item.qty
				else:
					# console("append reserve").log()
					warehouse_data.append({
					"warehouse":item.og_warehouse,
					"qty":0,
					"reserved":item.qty,
					"batch_id":item.batch_id
				})
			else:
				if any(d['warehouse'] == item.warehouse and d['batch_id'] == item.batch_id for d in warehouse_data):
					# console("modify qty").log()
					# console(item).log()
					for data in warehouse_data:
						if data['warehouse'] == item.warehouse and data['batch_id'] == item.batch_id:
							data['qty'] = item.qty
				else:
					# console("append qty").log()
					warehouse_data.append({
						"warehouse":item.warehouse,
						"qty":item.qty,
						"batch_id":item.batch_id,
						"reserved":0
					})
			# console(warehouse_data).log()


		# frappe.throw(str(raw_batch_data))
		return warehouse_data,sn_bn

	else:
		actual_data = frappe.db.sql("""
		select bn.warehouse,bn.actual_qty,wh.is_reserve_warehouse,wh.warehouse as og_warehouse from `tabBin` bn inner join `tabWarehouse` wh on wh.name = bn.warehouse where bn.actual_qty > 0 and bn.item_code = %s 
		""",product_id,as_dict = 1)
		
		for item in actual_data:
			if item.is_reserve_warehouse:
				if any(d['warehouse'] == item.og_warehouse for d in warehouse_data):
					for data in warehouse_data:
						if data['warehouse'] == item.og_warehouse:
							data['reserved'] = item.actual_qty

				else:
					warehouse_data.append({
					"warehouse":item.og_warehouse,
					"qty":0,
					"reserved":item.actual_qty
				})
			else:
				warehouse_data.append({
					"warehouse":item.warehouse,
					"qty":item.actual_qty,
					"reserved":0
				})
			
		return warehouse_data,sn_bn




	# 
	

	# warehouse_data = []
	# for item in actual_data:
	# 	if item.is_reserve_warehouse:
	# 		if any(d['warehouse'] == item.og_warehouse for d in warehouse_data):
	# 			for data in warehouse_data:
	# 				if data['warehouse'] == item.og_warehouse:
	# 					data['reserved'] = item.actual_qty

	# 		else:
	# 			warehouse_data.append({
	# 			"warehouse":item.og_warehouse,
	# 			"qty":0,
	# 			"reserved":item.actual_qty,
	# 			"serial_no":"",
	# 			"batch_no":"",
	# 			"has_serial_no":item.has_serial_no,
	# 			"has_batch_no":item.has_batch_no
	# 		})
				
	# 	else:	
	# 		serial_no_str=""
	# 		batch_no_str=""
	# 		# frappe.msgprint(str(item.has_serial_no))
	# 		# frappe.msgprint(str(item.has_batch_no))
	# 		if item.has_serial_no:	
	# 			frappe.msgprint("serial no")		
	# 			serial_no = frappe.db.sql("""
	# 			select name from `tabSerial No` where status = 'Active' and item_code = %s and warehouse = %s
	# 			""",(product_id,item.warehouse),as_dict = 1)
	# 			# frappe.msgprint(str(serial_no))
	# 			serial_no_str = ",".join([item['name'] for item in serial_no])
	# 			# frappe.msgprint(serial_no_str)
	# 		if item.has_batch_no:
	# 			# frappe.msgprint("batch no")
	# 			batch = get_batches(product_id, item.warehouse)

	# 			batch_no_str = ",".join([str(item['batch_id'])+" | <b>"+str(item['qty'])+"</b>" for item in batch])
	# 			# frappe.throw(str(batch))

	# 		warehouse_data.append({
	# 			"warehouse":item.warehouse,
	# 			"qty":item.actual_qty,
	# 			"reserved":0,
	# 			"serial_no":serial_no_str,
	# 			"batch_no":batch_no_str,
	# 			"has_serial_no":item.has_serial_no,
	# 			"has_batch_no":item.has_batch_no

	# 		})
	# return warehouse_data

def prepare_warehousewise_data(sn_bn,data):
	warehouse_data = []
	if sn_bn[0]:
		pass
	elif sn_bn[1]:
		for item in data:
			if item.is_reserve_warehouse:
				if any(d['warehouse'] == item.og_warehouse for d in warehouse_data):
					for data in warehouse_data:
						if data['warehouse'] == item.og_warehouse:
							data['reserved'] = item.actual_qty

				else:
					warehouse_data.append({
					"warehouse":item.og_warehouse,
					"qty":0,
					"reserved":item.actual_qty
				})
			else:
				warehouse_data.append({
					"warehouse":item.warehouse,
					"qty":item.actual_qty,
					"reserved":0
				})
		

	else:
		for item in data:
			if item.is_reserve_warehouse:
				if any(d['warehouse'] == item.og_warehouse for d in warehouse_data):
					for data in warehouse_data:
						if data['warehouse'] == item.og_warehouse:
							data['reserved'] = item.actual_qty

				else:
					warehouse_data.append({
					"warehouse":item.og_warehouse,
					"qty":0,
					"reserved":item.actual_qty
				})
			else:
				warehouse_data.append({
					"warehouse":item.warehouse,
					"qty":item.actual_qty,
					"reserved":0
				})
		
		
		



		
		
	# frappe.throw(warehouse_data)


	# warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")

	# data = frappe.db.sql("""
	# 	select 
	# 	i.name,
	# 	i.item_name,
	# 	sle.qty_after_transaction,
	# 	sle.warehouse
	# 	from
	# 	`tabItem` i
	# 	left join (
	# 	select item_code, qty_after_transaction, warehouse
	# 	from
	# 	`tabStock Ledger Entry`
	# 	group by item_code, warehouse
	# 	order by creation desc
	# 	) sle on sle.item_code = i.name
	# 	where
	# 	sle.warehouse <> %s
	# 	and
	# 	i.name = %s
		
	# """, (warehouse, product_id), as_dict = True)

	# return data

@frappe.whitelist()
def get_sales_order(product_id):
	# product_id = 'Tubelight'

	data = frappe.db.sql("""
		select
		sii.creation,
		sii.parent,
		sii.uom,
		sii.qty,
		sii.rate,
		si.customer
		from
		`tabSales Invoice Item` sii
		left join `tabSales Invoice` si on si.name = sii.parent
		where item_code = %s
		and si.docstatus = 1
		order by creation desc
		limit 6
		
	""", (product_id), as_dict = True)
	
	return data

@frappe.whitelist()
def get_purchase_order(product_id):
	# product_id = 'Phone'

	data = frappe.db.sql("""
		select
		pii.creation,
		pii.parent,
		pii.uom,
		pii.qty,
		pii.rate,
		pi.supplier
		from
		`tabPurchase Invoice Item` pii
		left join `tabPurchase Invoice` pi on pi.name = pii.parent
		where pii.item_code = %s
		and pi.docstatus = 1
		order by creation desc
		limit 6

		""", (product_id),as_dict = True)
	return data

@frappe.whitelist()
def get_pending_po(product_id):
	# product_id = 'Phone'

	data = frappe.db.sql("""
		select
		poi.creation,
		poi.parent,
		poi.uom,
		poi.qty,
		poi.rate,
		po.supplier
		from
		`tabPurchase Order Item` poi
		left join `tabPurchase Order` po on po.name = poi.parent
		where poi.item_code = %s
		and po.docstatus = 1
		and po.name not in (select purchase_order from `tabPurchase Invoice Item`)
		order by creation desc
		limit 6

		""", (product_id),as_dict = True)
	return data

@frappe.whitelist()
def get_pending_so(product_id):
	# product_id = 'Phone'

	data = frappe.db.sql("""
		select
		soi.creation,
		soi.parent,
		soi.uom,
		soi.qty,
		soi.rate,
		so.customer
		from
		`tabSales Order Item` soi
		left join `tabSales Order` so on so.name = soi.parent
		where soi.item_code = %s
		and so.docstatus = 1
		and so.name not in (select sales_order from `tabSales Invoice Item`)
		order by creation desc
		limit 6
		
	""", (product_id),as_dict = True)
	return data
