frappe.ui.form.on('Sales Order', {
	refresh(frm) {
        if(frm.doc.docstatus == 1){
		cur_frm.add_custom_button(__("Create Pick List"), function() {
            make_pick_list(frm)
         }); 
        }
	},
    
});

var make_pick_list = function(frm) {
    frappe.model.open_mapped_doc({
        method: "nanak_customization.nanak_customization.doctype.nanak_pick_list.nanak_pick_list.make_pick_list",
        frm: frm
    })
}