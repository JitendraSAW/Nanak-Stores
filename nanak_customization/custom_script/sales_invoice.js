frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
        if(frm.doc.docstatus == 1 && frm.doc.picklist_reference){
            frm.add_custom_button(__("Unlink Nanak Picklist"), function() {
                frappe.call({
                    method: 'nanak_customization.nanak_customization.sales_invoice.unlink_vouchers',
                    args: {
                        'nanak_pick_list': frm.doc.picklist_reference,
                        "sales_invoice":frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message === "success") {
                            frappe.msgprint(__('Vouchers unlinked successfully.'));
                            frm.reload_doc();
                        }else {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: __('Failed to unlink vouchers. Please try again.')
                            });
                        }
                    }
                });
                
            }); 
        }
	},
    
});

