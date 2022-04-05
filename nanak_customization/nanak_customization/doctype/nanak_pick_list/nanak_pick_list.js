// Copyright (c) 2022, Raaj Tailor and contributors
// For license information, please see license.txt




{% include 'erpnext/selling/sales_common.js' %};




//Set Warehouse on popup button click
  $(document).on('click', '.add-warehouse', function(){
	  cur_frm.set_value('set_warehouse',$(this).attr('data'))
	  cur_frm.trigger('set_warehouse')
	  cur_frm.refresh_field('set_warehouse')
	  cur_dialog.hide()
	});
	$(document).on('click', '.btn-modal-primary', function(){
		if(!cur_frm.doc.set_warehouse){
			cur_frm.set_value("set_warehouse",cur_frm.doc.items[cur_frm.doc.items.length - 1].warehouse)
			cur_frm.refresh_field("set_warehouse")
		}
	  });


cur_frm.add_fetch('customer', 'tax_id', 'tax_id');
frappe.provide("erpnext.stock");
frappe.provide("erpnext.stock.delivery_note");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Nanak Pick List", {
	
	is_pos:function(frm){
		if(frm.doc.is_pos){
			frappe.db.get_doc('Mode of Payment', 'Cash')
			.then(doc => {
				console.log(doc)
				if(doc){
					var newrow = frappe.model.add_child(frm.doc, "Nanak Pick List Payments", "payments");
					newrow.mode_of_payment = doc.mode_of_payment
					newrow.type = doc.type
					newrow.account = doc.accounts[0].default_account
					refresh_field("payments");
					""
				}
			})
	


refresh_field("items");

		}
	},
	

	//clear warehouse button
	clear_warehouse:function(frm) {
		frm.set_value("set_warehouse","")
		frm.refresh_field("set_warehouse")
	},
	setup: function(frm) {

		frm.custom_make_buttons = {
			'Sales Invoice': 'Sales Invoice',
		},
		frm.set_indicator_formatter('item_code',
			function(doc) {
				return (doc.docstatus==1 || doc.qty<=doc.actual_qty) ? "green" : "orange"
			})

		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});
		erpnext.queries.setup_warehouse_query(frm);

		frm.set_query('expense_account', 'items', function(doc, cdt, cdn) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						"report_type": "Profit and Loss",
						"company": doc.company,
						"is_group": 0
					}
				}
			}
		});

		frm.set_query('transporter', function(doc) {
			
				return {
					filters: {
						"is_transporter": 1
						
					}
				}
			
		});

		frm.set_query('cost_center', 'items', function(doc, cdt, cdn) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						'company': doc.company,
						"is_group": 0
					}
				}
			}
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);

		frm.set_df_property('packed_items', 'cannot_add_rows', true);
		frm.set_df_property('packed_items', 'cannot_delete_rows', true);
	},
	customer:function(frm){
		if(frm.doc.customer){
			// frappe.call({
			// 	"method":"nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.get_credit_days",
			// 	"args":{
			// 		"customer":frm.doc.customer,
			// 		"company":frm.doc.company,
			// 		"date":frm.doc.posting_date
			// 	}
			// })
			get_party_details(frm)
			// get_tax_template(frm)
			// set_taxes_from_address(frm)
			// set_taxes(frm)

			frm.trigger("get_customer_outstanding")
			
		}
		
	},

	print_without_amount: function(frm) {
		erpnext.stock.delivery_note.set_print_hide(frm.doc);
	},
	//Get Customer Outsatnding on customer selection
	get_customer_outstanding(frm){
		var end_date = frappe.datetime.add_months(cur_frm.doc.posting_date, -3);
		// console.log(end_date)

		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				'doctype': 'Sales Invoice',
				'filters':[['customer','=',frm.doc.customer],['docstatus','=',1],['outstanding_amount','>',0],['posting_date','>',end_date]],
				'fields': [
					'name',
					
				]
			},
			callback: function(r) {
				if (!r.exc) {
					// console.log(r.message)
					if(!r.message.length > 0){
						frappe.msgprint("This Customer Does not have any transaction in past 180 days.")
					}
				}
			}
		});
		
	},

	refresh: function(frm) {
		change_color_code(frm)		

		if(frm.doc.customer){
			frm.add_custom_button("Check Past Transactions", function(){
				frm.trigger("get_customer_outstanding")
			});
		}
		
	}
});

frappe.ui.form.on("Nanak Pick List Item", {
	// Item popup to select
	// items_add(frm){
	// 	console.log("add item")
	// 	frappe.call({
	// 		"method":"nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.check_credit_limit",
	// 		"args":{
	// 			"customer":frm.doc.customer,
	// 			"company":frm.doc.company,
	// 			"extra_amount":frm.doc.grand_total
				
	// 		},
	// 		"callback":function(res){
	// 			console.log(res)
	// 		}
	// 	})
	// },
	item_code:function(frm,cdt,cdn){
		var row = locals[cdt][cdn]
		if(row.item_code){
		frappe.db.get_value("Item", row.item_code, ["has_batch_no", "has_serial_no"])
		.then((r) => {
			if (r.message &&
			(!r.message.has_batch_no && !r.message.has_serial_no)) {
				frappe.call({
					"method":"nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.check_item_stock",
					"args":{
						"item":row.item_code,
						"set_warehouse":frm.doc.set_warehouse
					},
					"callback":function(res){
						// console.log(res)
						if(res.message == 0){
							row.item_code = ""
							frm.refresh_field("items")
						}
					}
				})
			}else{
				frappe.call({
					"method":"nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.check_item_stock_bs",
					"args":{
						"item":row.item_code,
						"set_warehouse":frm.doc.set_warehouse
					},
					"callback":function(res){
						// console.log(res)
						if(res.message == 0){
							row.item_code = ""
							frm.refresh_field("items")
							frappe.flags.hide_serial_batch_dialog = true;
						}
					}
				})
			}
		});
		}
		
		
			
		
	},

	dereserve:function(frm,cdt,cdn){
		var row = locals[cdt][cdn]
		if(frm.doc.docstatus == 1){
			frappe.call({
				"method":"nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.dereserve_stock",
				"args":{
					"item_reference":row.name,
					"so_detail":row.so_detail,
					"curr_qty":row.qty
					
				},
				"callback":function(res){
					// console.log(res)
					if(res.message){
						frappe.db.set_value("Nanak Pick List Item",row.name,"dereserved",1)
						frappe.msgprint("Item has been dereserved!")
					}
				}
			})
		}
	},

	expense_account: function(frm, dt, dn) {
		var d = locals[dt][dn];
		frm.update_in_all_rows('items', 'expense_account', d.expense_account);
	},
	cost_center: function(frm, dt, dn) {
		var d = locals[dt][dn];
		frm.update_in_all_rows('items', 'cost_center', d.cost_center);
	},
	check_stock : function(frm, dt, dn){
		var row = locals[dt][dn]
		if(row.item_code){
			frappe.call({
				"method":"nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.check_item_stock",
				"args":{
					"item":row.item_code
				}
			})
		}else{
			frappe.msgprint("Please enter Item to Check Stock!")
		}
	}
});

var change_color_code = function (frm) {
	
	frm.doc.items.forEach(function (child) {
	 
	  if (child.dereserved == 1) {
		var sel = 'div[data-fieldname="items"]';
  
		var row_rate = $(sel)
		  .find('.form-grid')
		  .find('.grid-body')
		  .find('.rows')
		  .find('[data-idx="' + child.idx + '"]');
		row_rate.css('font-weight', 'bold');
		row_rate.css('background-color', 'rgba(255, 0, 0)');
	  }
	});
  };

erpnext.stock.NanakPickList = erpnext.selling.SellingController.extend({
	//override tranasction.js methods
	setup_quality_inspection: function() {
		// if(!in_list(["Delivery Note", "Sales Invoice", "Purchase Receipt", "Purchase Invoice","Nanak Pick List"], this.frm.doc.doctype)) {
		// 	return;
		// }

		// const me = this;
		// if (!this.frm.is_new() && this.frm.doc.docstatus === 0) {
		// 	this.frm.add_custom_button(__("Quality Inspection(s)"), () => {
		// 		me.make_quality_inspection();
		// 	}, __("Create"));
		// 	this.frm.page.set_inner_btn_group_as_primary(__('Create'));
		// }

		// const inspection_type = in_list(["Purchase Receipt", "Purchase Invoice"], this.frm.doc.doctype)
		// 	? "Incoming" : "Outgoing";

		// let quality_inspection_field = this.frm.get_docfield("items", "quality_inspection");
		// quality_inspection_field.get_route_options_for_new_doc = function(row) {
		// 	if(me.frm.is_new()) return;
		// 	return {
		// 		"inspection_type": inspection_type,
		// 		"reference_type": me.frm.doc.doctype,
		// 		"reference_name": me.frm.doc.name,
		// 		"item_code": row.doc.item_code,
		// 		"description": row.doc.description,
		// 		"item_serial_no": row.doc.serial_no ? row.doc.serial_no.split("\n")[0] : null,
		// 		"batch_no": row.doc.batch_no
		// 	}
		// }

		// this.frm.set_query("quality_inspection", "items", function(doc, cdt, cdn) {
		// 	let d = locals[cdt][cdn];
		// 	return {
		// 		filters: {
		// 			docstatus: 1,
		// 			inspection_type: inspection_type,
		// 			reference_name: doc.name,
		// 			item_code: d.item_code
		// 		}
		// 	}
		// });
	},

	item_code: function(doc, cdt, cdn) {
		var me = this;
		var item = frappe.get_doc(cdt, cdn);
		var update_stock = 0, show_batch_dialog = 0;
		if(['Sales Invoice'].includes(this.frm.doc.doctype)) {
			update_stock = cint(me.frm.doc.update_stock);
			show_batch_dialog = update_stock;

		} else if((this.frm.doc.doctype === 'Purchase Receipt' && me.frm.doc.is_return) ||
			this.frm.doc.doctype === 'Delivery Note' || this.frm.doc.doctype === "Nanak Pick List") {
			show_batch_dialog = 1;
		}
		// clear barcode if setting item (else barcode will take priority)
		if (this.frm.from_barcode == 0) {
			item.barcode = null;
		}
		this.frm.from_barcode = this.frm.from_barcode - 1 >= 0 ? this.frm.from_barcode - 1 : 0;


		if(item.item_code || item.barcode || item.serial_no) {
			if(!this.validate_company_and_party()) {
				this.frm.fields_dict["items"].grid.grid_rows[item.idx - 1].remove();
			} else {
				return this.frm.call({
					method: "erpnext.stock.get_item_details.get_item_details",
					child: item,
					args: {
						doc: me.frm.doc,
						args: {
							overwrite_warehouse:false,
							item_code: item.item_code,
							barcode: item.barcode,
							serial_no: item.serial_no,
							batch_no: item.batch_no,
							set_warehouse: me.frm.doc.set_warehouse,
							warehouse: me.frm.doc.set_warehouse,
							customer: me.frm.doc.customer || me.frm.doc.party_name,
							quotation_to: me.frm.doc.quotation_to,
							supplier: me.frm.doc.supplier,
							currency: me.frm.doc.currency,
							update_stock: update_stock,
							conversion_rate: me.frm.doc.conversion_rate,
							price_list: me.frm.doc.selling_price_list || me.frm.doc.buying_price_list,
							price_list_currency: me.frm.doc.price_list_currency,
							plc_conversion_rate: me.frm.doc.plc_conversion_rate,
							company: me.frm.doc.company,
							order_type: me.frm.doc.order_type,
							is_pos: cint(me.frm.doc.is_pos),
							is_return: cint(me.frm.doc.is_return),
							is_subcontracted: me.frm.doc.is_subcontracted,
							transaction_date: me.frm.doc.transaction_date || me.frm.doc.posting_date,
							ignore_pricing_rule: me.frm.doc.ignore_pricing_rule,
							doctype: me.frm.doc.doctype,
							name: me.frm.doc.name,
							project: item.project || me.frm.doc.project,
							qty: item.qty || 1,
							net_rate: item.rate,
							stock_qty: item.stock_qty,
							conversion_factor: item.conversion_factor,
							weight_per_unit: item.weight_per_unit,
							weight_uom: item.weight_uom,
							manufacturer: item.manufacturer,
							stock_uom: item.stock_uom,
							pos_profile: '',
							cost_center: item.cost_center,
							tax_category: me.frm.doc.tax_category,
							item_tax_template: item.item_tax_template,
							child_docname: item.name
						}
					},

					callback: function(r) {
						if(!r.exc) {
							console.log(r)
							frappe.run_serially([
								() => {
									var d = locals[cdt][cdn];
									// console.log(me)
									me.add_taxes_from_item_tax_template(d.item_tax_rate);
									if (d.free_item_data) {
										me.apply_product_discount(d);
									}
								},
								() => {
									// for internal customer instead of pricing rule directly apply valuation rate on item
									if (me.frm.doc.is_internal_customer || me.frm.doc.is_internal_supplier) {
										me.get_incoming_rate(item, me.frm.posting_date, me.frm.posting_time,
											me.frm.doc.doctype, me.frm.doc.company);
									} else {
										me.frm.script_manager.trigger("price_list_rate", cdt, cdn);
									}
								},
								() => {
									if (me.frm.doc.is_internal_customer || me.frm.doc.is_internal_supplier) {
										me.calculate_taxes_and_totals();
									}
								},
								() => me.toggle_conversion_factor(item),
								() => {
									if (show_batch_dialog)
										return frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"])
											.then((r) => {
												if (r.message &&
												(r.message.has_batch_no || r.message.has_serial_no)) {
													frappe.flags.hide_serial_batch_dialog = false;
												}else{
													frappe.flags.hide_serial_batch_dialog = true;
												}
											});
								},
								() => {
									// check if batch serial selector is disabled or not
									if (show_batch_dialog && !frappe.flags.hide_serial_batch_dialog)
										return frappe.db.get_single_value('Stock Settings', 'disable_serial_no_and_batch_selector')
											.then((value) => {
												if (value) {
													frappe.flags.hide_serial_batch_dialog = true;
												}
											});
								},
								() => {
									if(show_batch_dialog && !frappe.flags.hide_serial_batch_dialog) {
										var d = locals[cdt][cdn];
										$.each(r.message, function(k, v) {
											if(!d[k]) d[k] = v;
										});

										if (d.has_batch_no && d.has_serial_no) {
											d.batch_no = undefined;
										}

										erpnext.show_serial_batch_selector(me.frm, d, (item) => {
											me.frm.script_manager.trigger('qty', item.doctype, item.name);
											if (!me.frm.doc.set_warehouse)
												me.frm.script_manager.trigger('warehouse', item.doctype, item.name);
										}, undefined, !frappe.flags.hide_serial_batch_dialog);
									}
								},
								() => me.conversion_factor(doc, cdt, cdn, true),
								() => me.remove_pricing_rule(item),
								() => {
									if (item.apply_rule_on_other_items) {
										let key = item.name;
										me.apply_rule_on_other_items({key: item});
									}
								},
								() => {
									var company_currency = me.get_company_currency();
									me.update_item_grid_labels(company_currency);
								}
							]);
						}
					}
				});
			}
		}
	},

	price_list_rate: function(doc, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		frappe.model.round_floats_in(item, ["price_list_rate", "discount_percentage"]);

		// check if child doctype is Sales Order Item/Qutation Item and calculate the rate
		if (in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item", "POS Invoice Item", "Purchase Invoice Item", "Purchase Order Item", "Purchase Receipt Item","Nanak Pick List Item"]), cdt)
			this.apply_pricing_rule_on_item(item);
		else
			item.rate = flt(item.price_list_rate * (1 - item.discount_percentage / 100.0),
				precision("rate", item));

		this.calculate_taxes_and_totals();
	},

	company: function() {
		var me = this;
		var set_pricing = function() {
			if(me.frm.doc.company && me.frm.fields_dict.currency) {
				var company_currency = me.get_company_currency();
				var company_doc = frappe.get_doc(":Company", me.frm.doc.company);

				if (!me.frm.doc.currency) {
					me.frm.set_value("currency", company_currency);
				}

				if (me.frm.doc.currency == company_currency) {
					me.frm.set_value("conversion_rate", 1.0);
				}
				if (me.frm.doc.price_list_currency == company_currency) {
					me.frm.set_value('plc_conversion_rate', 1.0);
				}
				if (company_doc.default_letter_head) {
					if(me.frm.fields_dict.letter_head) {
						me.frm.set_value("letter_head", company_doc.default_letter_head);
					}
				}
				let selling_doctypes_for_tc = ["Sales Invoice", "Quotation", "Sales Order", "Delivery Note","Nanak Pick List"];
				if (company_doc.default_selling_terms && frappe.meta.has_field(me.frm.doc.doctype, "tc_name") &&
				selling_doctypes_for_tc.indexOf(me.frm.doc.doctype) != -1) {
					me.frm.set_value("tc_name", company_doc.default_selling_terms);
				}
				let buying_doctypes_for_tc = ["Request for Quotation", "Supplier Quotation", "Purchase Order",
					"Material Request", "Purchase Receipt"];
				// Purchase Invoice is excluded as per issue #3345
				if (company_doc.default_buying_terms && frappe.meta.has_field(me.frm.doc.doctype, "tc_name") &&
				buying_doctypes_for_tc.indexOf(me.frm.doc.doctype) != -1) {
					me.frm.set_value("tc_name", company_doc.default_buying_terms);
				}

				frappe.run_serially([
					() => me.frm.script_manager.trigger("currency"),
					() => me.apply_default_taxes(),
					() => me.apply_pricing_rule(),
					() => me.calculate_taxes_and_totals()
				]);
			}
		}

		var set_party_account = function(set_pricing) {
			if (in_list(["Sales Invoice", "Purchase Invoice"], me.frm.doc.doctype)) {
				if(me.frm.doc.doctype=="Sales Invoice") {
					var party_type = "Customer";
					var party_account_field = 'debit_to';
				} else {
					var party_type = "Supplier";
					var party_account_field = 'credit_to';
				}

				var party = me.frm.doc[frappe.model.scrub(party_type)];
				if(party && me.frm.doc.company) {
					return frappe.call({
						method: "erpnext.accounts.party.get_party_account",
						args: {
							company: me.frm.doc.company,
							party_type: party_type,
							party: party
						},
						callback: function(r) {
							if(!r.exc && r.message) {
								me.frm.set_value(party_account_field, r.message);
								set_pricing();
							}
						}
					});
				} else {
					set_pricing();
				}
			} else {
				set_pricing();
			}

		}

		if (frappe.meta.get_docfield(this.frm.doctype, "shipping_address") &&
			in_list(['Purchase Order', 'Purchase Receipt', 'Purchase Invoice'], this.frm.doctype)) {
			erpnext.utils.get_shipping_address(this.frm, function(){
				set_party_account(set_pricing);
			});

			// Get default company billing address in Purchase Invoice, Order and Receipt
			frappe.call({
				'method': 'frappe.contacts.doctype.address.address.get_default_address',
				'args': {
					'doctype': 'Company',
					'name': this.frm.doc.company
				},
				'callback': function(r) {
					me.frm.set_value('billing_address', r.message);
				}
			});

		} else {
			set_party_account(set_pricing);
		}

		if(this.frm.doc.company) {
			erpnext.last_selected_company = this.frm.doc.company;
		}
	},

	set_margin_amount_based_on_currency: function(exchange_rate) {
		if (in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Purchase Invoice", "Purchase Order", "Purchase Receipt","Nanak Pick List"]), this.frm.doc.doctype) {
			var me = this;
			$.each(this.frm.doc.items || [], function(i, d) {
				if(d.margin_type == "Amount") {
					frappe.model.set_value(d.doctype, d.name, "margin_rate_or_amount",
						flt(d.margin_rate_or_amount) / flt(exchange_rate));
				}
			});
		}
	},

	get_exchange_rate: function(transaction_date, from_currency, to_currency, callback) {
		var args;
		if (["Quotation", "Sales Order", "Delivery Note", "Sales Invoice","Nanak Pick List"].includes(this.frm.doctype)) {
			args = "for_selling";
		}
		else if (["Purchase Order", "Purchase Receipt", "Purchase Invoice"].includes(this.frm.doctype)) {
			args = "for_buying";
		}

		if (!transaction_date || !from_currency || !to_currency) return;
		return frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				transaction_date: transaction_date,
				from_currency: from_currency,
				to_currency: to_currency,
				args: args
			},
			freeze: true,
			freeze_message: __("Fetching exchange rates ..."),
			callback: function(r) {
				callback(flt(r.message));
			}
		});
	},

	_get_item_list: function(item) {
		var item_list = [];
		var append_item = function(d) {
			if (d.item_code) {
				item_list.push({
					"doctype": d.doctype,
					"name": d.name,
					"child_docname": d.name,
					"item_code": d.item_code,
					"item_group": d.item_group,
					"brand": d.brand,
					"qty": d.qty,
					"stock_qty": d.stock_qty,
					"uom": d.uom,
					"stock_uom": d.stock_uom,
					"parenttype": d.parenttype,
					"parent": d.parent,
					"pricing_rules": d.pricing_rules,
					"warehouse": d.warehouse,
					"serial_no": d.serial_no,
					"batch_no": d.batch_no,
					"price_list_rate": d.price_list_rate,
					"conversion_factor": d.conversion_factor || 1.0
				});

				// if doctype is Quotation Item / Sales Order Iten then add Margin Type and rate in item_list
				if (in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item",  "Purchase Invoice Item", "Purchase Order Item", "Purchase Receipt Item","Nanak Pick List Item"]), d.doctype) {
					item_list[0]["margin_type"] = d.margin_type;
					item_list[0]["margin_rate_or_amount"] = d.margin_rate_or_amount;
				}
			}
		};

		if (item) {
			append_item(item);
		} else {
			$.each(this.frm.doc["items"] || [], function(i, d) {
				append_item(d);
			});
		}
		return item_list;
	},

	//override tranasction.js methods


	//override method of taxes and totals
	calculate_taxes_and_totals: function(update_paid_amount) {
		this.discount_amount_applied = false;
		this._calculate_taxes_and_totals();
		this.calculate_discount_amount();

		// Advance calculation applicable to Sales /Purchase Invoice
		if(in_list(["Sales Invoice", "POS Invoice", "Purchase Invoice"], this.frm.doc.doctype)
			&& this.frm.doc.docstatus < 2 && !this.frm.doc.is_return) {
			this.calculate_total_advance(update_paid_amount);
		}

		if (in_list(["Sales Invoice", "POS Invoice"], this.frm.doc.doctype) && this.frm.doc.is_pos &&
			this.frm.doc.is_return) {
			this.update_paid_amount_for_return();
		}

		// Sales person's commission
		if(in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice","Nanak Pick List"], this.frm.doc.doctype)) {
			this.calculate_commission();
			this.calculate_contribution();
		}

		// Update paid amount on return/debit note creation
		if(this.frm.doc.doctype === "Purchase Invoice" && this.frm.doc.is_return
			&& (this.frm.doc.grand_total > this.frm.doc.paid_amount)) {
			this.frm.doc.paid_amount = flt(this.frm.doc.grand_total, precision("grand_total"));
		}

		this.frm.refresh_fields();
	},

	calculate_totals: function() {
		// Changing sequence can because of rounding adjustment issue and on-screen discrepancy
		var me = this;
		var tax_count = this.frm.doc["taxes"] ? this.frm.doc["taxes"].length : 0;
		this.frm.doc.grand_total = flt(tax_count
			? this.frm.doc["taxes"][tax_count - 1].total + flt(this.frm.doc.rounding_adjustment)
			: this.frm.doc.net_total);

		if(in_list(["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "POS Invoice","Nanak Pick List"], this.frm.doc.doctype)) {
			this.frm.doc.base_grand_total = (this.frm.doc.total_taxes_and_charges) ?
				flt(this.frm.doc.grand_total * this.frm.doc.conversion_rate) : this.frm.doc.base_net_total;
		} else {
			// other charges added/deducted
			this.frm.doc.taxes_and_charges_added = this.frm.doc.taxes_and_charges_deducted = 0.0;
			if(tax_count) {
				$.each(this.frm.doc["taxes"] || [], function(i, tax) {
					if (in_list(["Valuation and Total", "Total"], tax.category)) {
						if(tax.add_deduct_tax == "Add") {
							me.frm.doc.taxes_and_charges_added += flt(tax.tax_amount_after_discount_amount);
						} else {
							me.frm.doc.taxes_and_charges_deducted += flt(tax.tax_amount_after_discount_amount);
						}
					}
				});

				frappe.model.round_floats_in(this.frm.doc,
					["taxes_and_charges_added", "taxes_and_charges_deducted"]);
			}

			this.frm.doc.base_grand_total = flt((this.frm.doc.taxes_and_charges_added || this.frm.doc.taxes_and_charges_deducted) ?
				flt(this.frm.doc.grand_total * this.frm.doc.conversion_rate) : this.frm.doc.base_net_total);

			this.set_in_company_currency(this.frm.doc,
				["taxes_and_charges_added", "taxes_and_charges_deducted"]);
		}

		this.frm.doc.total_taxes_and_charges = flt(this.frm.doc.grand_total - this.frm.doc.net_total
			- flt(this.frm.doc.rounding_adjustment), precision("total_taxes_and_charges"));

		this.set_in_company_currency(this.frm.doc, ["total_taxes_and_charges", "rounding_adjustment"]);

		// Round grand total as per precision
		frappe.model.round_floats_in(this.frm.doc, ["grand_total", "base_grand_total"]);

		// rounded totals
		this.set_rounded_total();
	},
	//override method of taxes and totals
	
// Override logic for all by default function
// Wherever Delivery note appear in method, add nanak picklist to run same function in picklist 

	setup: function(doc) {
		this.setup_posting_date_time_check();
		this._super(doc);
		
	},
	refresh: function(doc, dt, dn) {
		var me = this;
		this._super();		

		if (doc.docstatus > 0) {
			this.show_stock_ledger();
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				this.show_general_ledger();
			}
			
		}

		if(doc.docstatus==1 && !doc.is_return && doc.status!="Closed" && flt(doc.per_billed) < 100) {
			

			
				this.frm.add_custom_button(__('Sales Invoice'), function() { me.make_sales_invoice() },
					__('Create'));
			
		}
	
		erpnext.stock.delivery_note.set_print_hide(doc, dt, dn);

		
	},
	make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.make_sales_invoice",
			frm: this.frm
		})
	},	
	tc_name: function() {
		this.get_terms();
	},
	items_on_form_rendered: function(doc, grid_row) {
		erpnext.setup_serial_or_batch_no();
	},
	packed_items_on_form_rendered: function(doc, grid_row) {
		erpnext.setup_serial_or_batch_no();
	},
});

$.extend(cur_frm.cscript, new erpnext.stock.NanakPickList({frm: cur_frm}));

frappe.ui.form.on('Nanak Pick List', {
	setup: function(frm) {
		if(frm.doc.company) {
			frm.trigger("unhide_account_head");
		}
	},
	company: function(frm) {
		frm.trigger("unhide_account_head");
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},
	unhide_account_head: function(frm) {		
		var aii_enabled = erpnext.is_perpetual_inventory_enabled(frm.doc.company)
		frm.fields_dict["items"].grid.set_column_disp(["expense_account", "cost_center"], aii_enabled);
	}
})

erpnext.stock.delivery_note.set_print_hide = function(doc, cdt, cdn){
	var dn_fields = frappe.meta.docfield_map['Nanak Pick List'];
	var dn_item_fields = frappe.meta.docfield_map['Nanak Pick List Item'];
	var dn_fields_copy = dn_fields;
	var dn_item_fields_copy = dn_item_fields;
	if (doc.print_without_amount) {
		dn_fields['currency'].print_hide = 1;
		dn_item_fields['rate'].print_hide = 1;
		dn_item_fields['discount_percentage'].print_hide = 1;
		dn_item_fields['price_list_rate'].print_hide = 1;
		dn_item_fields['amount'].print_hide = 1;
		dn_item_fields['discount_amount'].print_hide = 1;
		dn_fields['taxes'].print_hide = 1;
	} else {
		if (dn_fields_copy['currency'].print_hide != 1)
			dn_fields['currency'].print_hide = 0;
		if (dn_item_fields_copy['rate'].print_hide != 1)
			dn_item_fields['rate'].print_hide = 0;
		if (dn_item_fields_copy['amount'].print_hide != 1)
			dn_item_fields['amount'].print_hide = 0;
		if (dn_item_fields_copy['discount_amount'].print_hide != 1)
			dn_item_fields['discount_amount'].print_hide = 0;
		if (dn_fields_copy['taxes'].print_hide != 1)
			dn_fields['taxes'].print_hide = 0;
	}
}


erpnext.show_serial_batch_selector = function (frm, d, callback, on_close, show_dialog) {
	let warehouse, receiving_stock, existing_stock;
	if (frm.doc.is_return) {
		if (["Purchase Receipt", "Purchase Invoice"].includes(frm.doc.doctype)) {
			existing_stock = true;
			warehouse = d.warehouse;
		} else if (["Delivery Note", "Sales Invoice","Nanak Pick List"].includes(frm.doc.doctype)) {
			receiving_stock = true;
		}
	} else {
		if (frm.doc.doctype == "Stock Entry") {
			if (frm.doc.purpose == "Material Receipt") {
				receiving_stock = true;
			} else {
				existing_stock = true;
				warehouse = d.s_warehouse;
			}
		} else {
			existing_stock = true;
			warehouse = d.warehouse;
		}
	}

	if (!warehouse) {
		if (receiving_stock) {
			warehouse = ["like", ""];
		} else if (existing_stock) {
			warehouse = ["!=", ""];
		}
	}

	frappe.require("assets/erpnext/js/utils/serial_no_batch_selector.js", function() {
		new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: d,
			warehouse_details: {
				type: "Warehouse",
				name: warehouse
			},
			callback: callback,
			on_close: on_close
		}, show_dialog);
	});
}


var get_party_details = function(frm, method, args, callback) {
	// console.log("party details")
	if (!method) {
		method = "erpnext.accounts.party.get_party_details";
	}

	if (args) {
		if (in_list(['Sales Invoice', 'Sales Order', 'Nanak Pick List'], frm.doc.doctype)) {
			if (frm.doc.company_address && (!args.company_address)) {
				args.company_address = frm.doc.company_address;
			}
		}

		if (in_list(['Purchase Invoice', 'Purchase Order', 'Purchase Receipt'], frm.doc.doctype)) {
			if (frm.doc.shipping_address && (!args.shipping_address)) {
				args.shipping_address = frm.doc.shipping_address;
			}
		}
	}

	if (!args) {
		if ((frm.doctype != "Purchase Order" && frm.doc.customer)
			|| (frm.doc.party_name && in_list(['Quotation', 'Opportunity'], frm.doc.doctype))) {

			let party_type = "Customer";
			if (frm.doc.quotation_to && frm.doc.quotation_to === "Lead") {
				party_type = "Lead";
			}

			args = {
				party: frm.doc.customer || frm.doc.party_name,
				party_type: party_type,
				price_list: frm.doc.selling_price_list
			};
		} else if (frm.doc.supplier) {
			args = {
				party: frm.doc.supplier,
				party_type: "Supplier",
				bill_date: frm.doc.bill_date,
				price_list: frm.doc.buying_price_list
			};
		}

		if (in_list(['Sales Invoice', 'Sales Order', 'Nanak Pick List'], frm.doc.doctype)) {
			if (!args) {
				args = {
					party: frm.doc.customer || frm.doc.party_name,
					party_type: 'Customer'
				}
			}
			if (frm.doc.company_address && (!args.company_address)) {
				args.company_address = frm.doc.company_address;
			}

			if (frm.doc.shipping_address_name &&(!args.shipping_address_name)) {
				args.shipping_address_name = frm.doc.shipping_address_name;
			}
		}

		if (in_list(['Purchase Invoice', 'Purchase Order', 'Purchase Receipt'], frm.doc.doctype)) {
			if (!args) {
				args = {
					party: frm.doc.supplier,
					party_type: 'Supplier'
				}
			}

			if (frm.doc.shipping_address && (!args.shipping_address)) {
				args.shipping_address = frm.doc.shipping_address;
			}
		}

		if (args) {
			args.posting_date = frm.doc.posting_date || frm.doc.transaction_date;
			args.fetch_payment_terms_template = cint(!frm.doc.ignore_default_payment_terms_template);
		}
	}
	if (!args || !args.party) return;

	if (frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
		if (!erpnext.utils.validate_mandatory(frm, "Posting / Transaction Date",
			args.posting_date, args.party_type=="Customer" ? "customer": "supplier")) return;
	}

	if (!erpnext.utils.validate_mandatory(frm, "Company", frm.doc.company, args.party_type=="Customer" ? "customer": "supplier")) {
		return;
	}

	args.currency = frm.doc.currency;
	args.company = frm.doc.company;
	args.doctype = frm.doc.doctype;
	frappe.call({
		method: method,
		args: args,
		callback: function(r) {
			if (r.message) {
				frm.supplier_tds = r.message.supplier_tds;
				frm.updating_party_details = true;
				frappe.run_serially([
					() => frm.set_value(r.message),
					() => {
						frm.updating_party_details = false;
						if (callback) callback();
						frm.refresh();
						erpnext.utils.add_item(frm);
					}
				]);
			}
		}
	});
}







frappe.ui.form.on("Nanak Pick List", {
	onload:function(frm){
		frappe.call({
			"method":"nanak_customization.nanak_customization.regional_utils.get_gstins_for_company",
			"args":{
				
			},
			"freeze":true,
			"callback":function(r){
				// console.log(r.message[0][0])
				if(r.message){
					frm.set_value("company_gstin",r.message[0][0])
					frm.refresh_field("company_gstin")
				}
				
			}
		})
	},
	company_address: function(frm) {
		frm.trigger('get_tax_template');
	},
	shipping_address: function(frm) {
		frm.trigger('get_tax_template');
	},
	supplier_address: function(frm) {
		frm.trigger('get_tax_template');
	},
	tax_category: function(frm) {
		frm.trigger('get_tax_template');
	},
	customer_address: function(frm) {
		frm.trigger('get_tax_template');
	},
	get_tax_template: function(frm) {
		if (!frm.doc.company) return;

		let party_details = {
			'shipping_address': frm.doc.shipping_address || '',
			'shipping_address_name': frm.doc.shipping_address_name || '',
			'customer_address': frm.doc.customer_address || '',
			'supplier_address': frm.doc.supplier_address,
			'customer': frm.doc.customer,
			'supplier': frm.doc.supplier,
			'supplier_gstin': frm.doc.supplier_gstin,
			'company_gstin': frm.doc.company_gstin,
			'tax_category': frm.doc.tax_category
		};

		frappe.call({
			method: 'nanak_customization.nanak_customization.regional_utils.get_regional_address_details',
			args: {
				party_details: JSON.stringify(party_details),
				doctype: frm.doc.doctype,
				company: frm.doc.company
			},
			debounce: 2000,
			callback: function(r) {
				// console.log(r)
				if(r.message) {
					frm.set_value('taxes_and_charges', r.message.taxes_and_charges);
					frm.set_value('taxes', r.message.taxes);
					frm.set_value('place_of_supply', r.message.place_of_supply);
				}
			}
		});
	}
});