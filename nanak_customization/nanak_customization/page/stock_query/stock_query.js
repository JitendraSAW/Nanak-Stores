frappe.pages['stock-query'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Stock Query',
		single_column: true
	});

	new erpnext.StockQuery(page);
}

erpnext.StockQuery = class StockQuery {

	constructor(page) {
		this.page = page;
		this.make_form();
	}

	make_form() {
		this.form = new frappe.ui.FieldGroup({
			fields: [
				{
					label: __('Item Code'),
					fieldname: 'item_code',
					fieldtype: 'Link',
					options: 'Item',
					change: async () => {
						this.fetch_and_render()
					},
					get_query: () => {
						return {
							filters: {
								"disabled": ["!=", 1]
							}
						}
					},
				},
				{
					label: __('UOM'),
					fieldname: 'stock_uom',
					fieldtype: 'Data',
					
					
					read_only:1
					
				},
				{
					fieldtype: 'Column Break'
				},
				{
					label: __('Item Name'),
					fieldname: 'item_name',
					fieldtype: 'Data',
					
					change: () => {},
					read_only:1
					
				},
				{
					label: __('Item Group'),
					fieldname: 'item_group',
					fieldtype: 'Link',
					options: 'Item Group',
					change: () => {},
					read_only:1
					
				},
				{
					fieldtype: 'Column Break'
				},
				{
					label: __('Stock Category'),
					fieldname: 'stock_category',
					fieldtype: 'Data',
					
					change: () => {},
					read_only:1
					
				},
				{
					label: __('Company Code'),
					fieldname: 'company_code',
					fieldtype: 'Data',
					
					change: () => {},
					read_only:1
					
				},
				{
					fieldtype: 'Column Break'
				},
				
				{
					label: __('Price'),
					fieldname: 'price',
					fieldtype: 'Currency',
					
					change: () => {},
					read_only:1
					
				},
				
				{
					label: __('Qty'),
					fieldname: 'qty',
					fieldtype: 'Float',
					
					change: () => {},
					read_only:1
					
				},
				{
					fieldtype: 'Column Break'
				},
				{
					label: __('Tax'),
					fieldname: 'tax',
					fieldtype: 'Data',
					
					change: () => {},
					read_only:1
					
				},
				{
					label: __('HSN'),
					fieldname: 'gst_hsn_code',
					fieldtype: 'Data',
					
					change: () => {},
					read_only:1
					
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label:"Godownwise Stock",
					fieldtype: 'HTML',
					fieldname: 'stock'
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label:"Similar Items",
					fieldtype: 'HTML',
					fieldname: 'similar_items'
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label:"Sales",
					fieldtype: 'HTML',
					fieldname: 'sales'
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label:"Purchase",
					fieldtype: 'HTML',
					fieldname: 'purchase'
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label:"Pending PO",
					fieldtype: 'HTML',
					fieldname: 'pending_po'
				},
				{
					fieldtype: 'Section Break'
				},
				{
					label:"Pending SO",
					fieldtype: 'HTML',
					fieldname: 'pending_so'
				}
			],
			body: this.page.body
		});
		this.form.make();
		$(this.form.wrapper)
				.find(".input-with-feedback")
				.css({
					backgroundColor: '#cfcfcf'
				});
	}
	fetch_and_render(){
		// console.log(this.form.get_value("item_code"));
		var item_code = this.form.get_value("item_code");
		this.set_header_values(item_code)
		this.set_past_purchase(item_code)
		this.set_past_sales(item_code)
		this.set_similar_stock(item_code)
		this.set_warehouse_stock(item_code)
		this.set_pending_po(item_code)
		this.set_pending_so(item_code)
	}
	async set_header_values(item_code){
		// console.log(this.form.fields[1])
		var res = await get_header_list(item_code)
		// console.log(res)
		this.form.set_value("stock_uom",res.message[0].stock_uom)
		this.form.set_value("stock_category",res.message[0].stock_category)
		this.form.set_value("company_code",res.message[0].company_code)
		this.form.set_value("item_group",res.message[0].item_group)
		this.form.set_value("item_name",res.message[0].item_name)
		this.form.set_value("price",res.message[0].price)
		this.form.set_value("tax",res.message[0].item_tax_template)
		this.form.set_value("gst_hsn_code",res.message[0].gst_hsn_code)
		this.form.set_value("qty",res.message[0].qty)
	}
	async set_warehouse_stock(item_code){
		if(item_code){

		var res = await get_warehouse_stock(item_code)
		console.log(res)
		var html_content = '';
		html_content += '<div class="frappe-card"><h4>Warehouse Wise Stock</h4><table class="table"><thead><tr><th>Warehouse</th><th>Batch/Serial No</th><th>Open Qty</th><th>Reserve Qty</th></tr></thead><tbody>';
		res.message[0].forEach(i =>{
			console.log(i)
			if(res.message[1].has_serial_no){
				html_content +=
			'<tr>' +
				'<td>' + i.warehouse +'</td>' +
				'<td>' + i.serial_no +' </td>' +
				'<td>' + i.qty +'</td>' +
				'<td>' + i.reserved +' </td>' +
				
			'</tr>';
			}else if(res.message[1].has_batch_no){
				html_content +=
			'<tr>' +
				'<td>' + i.warehouse +'</td>' +
				'<td>' + i.batch_id +' </td>' +
				'<td>' + i.qty +'</td>' +
				'<td>' + i.reserved +' </td>' +
				
			'</tr>';
			}else{
				html_content +=
			'<tr>' +
				'<td>' + i.warehouse +'</td>' +
				'<td></td>' +
				'<td>' + i.qty +'</td>' +
				'<td>' + i.reserved +' </td>' +
				
			'</tr>';
			}
		})
		

		html_content += '</tbody></table></div>'

		this.form.get_field('stock').html(html_content);

		}
		
	}
	async set_similar_stock(item_code){
		var res = await get_similar_items(item_code)
		// console.log(res.message)
		var html_content = '';
		html_content += '<div class="frappe-card">' +
			'<h4>Similar Items</h4>' +
			'<table class="table">' +
			'<thead>' +
			'<tr>' +
				'<th>Item Code</th>' +
				'<th>Item Name</th>' +
				'<th>Qty</th>' +
			'</tr>' +
			'</thead>' +
			'<tbody>';
		for(var i in res.message){
			var link = 'item/' + encodeURI(res.message[i].name)
			html_content +=
			'<tr>' +
				'<td><a onclick="frappe.utils.copy_to_clipboard(\'' + res.message[i].name + '\')">' + res.message[i].name + '</a></td>' +
				'<td>' + res.message[i].item_name +'</td>' +
				'<td>' + res.message[i].qty +'</td>' +
			'</tr>';
		}
		
		html_content +=
			'</tbody>' +
			'</table>' +
			'</div>';

		this.form.get_field('similar_items').html(html_content);
	}
	async set_past_sales(item_code){
		var res = await get_sales_order(item_code)
		var html_content = '';

		html_content += '<div class="frappe-card"><h4>Past Sales</h4><table class="table"><thead><tr><th>Bill No</th><th>Bill Date</th><th>Party Name</th><th>Unit</th><th>Qty</th><th>Item Value</th></tr></thead><tbody>';

		for(var i in res.message){
			var link = 'sales-invoice/' + encodeURI(res.message[i].parent)
			html_content +=
			'<tr>' +
				'<td><a href=' + link.toString() + '>' + res.message[i].parent + '</a></td>' +
				'<td>' + res.message[i].creation +'</td>' +
				'<td>' + res.message[i].customer +'</td>' +
				'<td>' + res.message[i].uom +'</td>' +
				'<td>' + res.message[i].qty +'</td>' +
				'<td>' + res.message[i].rate +'</td>' +
			'</tr>';
		}

		html_content += '</tbody></table></table></div>';

		this.form.get_field('sales').html(html_content);
	}
	async set_past_purchase(item_code){
		var res = await get_purchase_order(item_code)

		var html_content = '';

		html_content += '<div class="frappe-card"><h4>Past Purchase</h4><table class="table"><thead><tr><th>Bill No</th><th>Bill Date</th><th>Party Name</th><th>Unit</th><th>Qty</th><th>Item Value</th></tr></thead><tbody>';

		for(var i in res.message){
			var link = 'purchase-invoice/' + encodeURI(res.message[i].parent)
			html_content +=
			'<tr>' +
				'<td><a href=' + link.toString() + '>' + res.message[i].parent + '</a></td>' +
				'<td>' + res.message[i].creation +'</td>' +
				'<td>' + res.message[i].supplier +'</td>' +
				'<td>' + res.message[i].uom +'</td>' +
				'<td>' + res.message[i].qty +'</td>' +
				'<td>' + res.message[i].rate +'</td>' +
			'</tr>';
		}

		html_content += '</tbody></table></table></div>';

		this.form.get_field('purchase').html(html_content);
	}
	async set_pending_so(item_code){
		var res = await get_pending_so(item_code)

		var html_content = '';

		html_content += '<div class="frappe-card"><h4>Pending Sales</h4><table class="table"><thead><tr><th>Bill No</th><th>Bill Date</th><th>Party Name</th><th>Unit</th><th>Qty</th><th>Item Value</th></tr></thead><tbody>';

		for(var i in res.message){
			var link = 'sales-order/' + encodeURI(res.message[i].parent)
			html_content +=
			'<tr>' +
				'<td><a href=' + link.toString() + '>' + res.message[i].parent + '</a></td>' +
				'<td>' + res.message[i].creation +'</td>' +
				'<td>' + res.message[i].customer +'</td>' +
				'<td>' + res.message[i].uom +'</td>' +
				'<td>' + res.message[i].qty +'</td>' +
				'<td>' + res.message[i].rate +'</td>' +
			'</tr>';
		}

		html_content += '</tbody></table></table></div>';

		this.form.get_field('pending_so').html(html_content);
	}
	async set_pending_po(item_code){
		var res = await get_pending_po(item_code)

		var html_content = '';

		html_content += '<div class="frappe-card"><h4>Pending Purchase</h4><table class="table"><thead><tr><th>Bill No</th><th>Bill Date</th><th>Party Name</th><th>Unit</th><th>Qty</th><th>Item Value</th></tr></thead><tbody>';

		for(var i in res.message){
			var link = 'purchase-order/' + encodeURI(res.message[i].parent)
			html_content +=
			'<tr>' +
				'<td><a href=' + link.toString() + '>' + res.message[i].parent + '</a></td>' +
				'<td>' + res.message[i].creation +'</td>' +
				'<td>' + res.message[i].customer +'</td>' +
				'<td>' + res.message[i].uom +'</td>' +
				'<td>' + res.message[i].qty +'</td>' +
				'<td>' + res.message[i].rate +'</td>' +
			'</tr>';
		}

		html_content += '</tbody></table></table></div>';

		this.form.get_field('pending_po').html(html_content);
	}
}


function get_header_list(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_header_data',
				'args': {
					'item_code': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

function get_similar_items(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_same_category',
				'args': {
					'product_id': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

function get_sales_order(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_sales_order',
				'args': {
					'product_id': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

function get_purchase_order(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_purchase_order',
				'args': {
					'product_id': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

function get_pending_po(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_pending_po',
				'args': {
					'product_id': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

function get_pending_so(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_pending_so',
				'args': {
					'product_id': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

function get_warehouse_stock(item) {
	return new Promise(function(resolve, reject){
		try{
			frappe.call({
				'method': 'nanak_customization.nanak_customization.page.stock_query.stock_query.get_godown_wise',
				'args': {
					'product_id': item
				},
				callback: resolve
			});
		} catch (e) {reject(e);}
	});
}

// function get_list (opts) {
// 	return new Promise(function (resolve, reject) {
// 		try {
// 			frappe.call({
// 				method: FRAPPE_CLIENT + '.get_list',
// 				args: {
// 					doctype: opts.doctype,
// 					fields: opts.fields,
// 					filters: opts.filters,
// 					order_by: opts.order_by,
// 					limit_start: opts.limit_start,
// 					limit_page_length: opts.limit_page_length,
// 					parent: opts.parent
// 				},
// 				callback: resolve
// 			});
// 		} catch (e) { reject(e); }
// 	});
// }


// refresh : async function(frm){
// let list_data = await get_list(ops)

// }
