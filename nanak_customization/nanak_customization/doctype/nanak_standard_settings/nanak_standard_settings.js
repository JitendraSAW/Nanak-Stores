// Copyright (c) 2022, Raaj Tailor and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nanak Standard Settings', {
	refresh: function(frm) {
		frm.add_custom_button("Update Pick Qty Data", function(){
			frappe.msgprint("hello")

			frappe.call('nanak_customization.nanak_customization.doctype.nanak_standard_settings.nanak_standard_settings.update_custom_picked_qty')
			.then(r => {
				console.log(r)
				// {message: "pong"}
			})
		  });
	}
});
