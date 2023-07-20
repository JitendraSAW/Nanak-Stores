frappe.ui.form.on("Quotation", {
    'onload_post_render': function(frm) {
        frm.fields_dict.items.grid.wrapper.on('click', 'input[data-fieldname="item_code"][data-doctype="Quotation Item"]', function(e) {
            console.log(e.type);
            $("div[data-fieldname='item_code'] .awesomplete > ul").css("min-width", "830px");
        });
    },

    refresh: function(frm) {
        console.log("setup query")
        if(frm.fields_dict["items"].grid.get_field('item_code')) {
            frm.set_query("item_code", "items", function() {
                return {
                    // query: "erpnext.controllers.queries.item_query",
                    query: "nanak_customization.nanak_customization.query.item_query.item_query",
                    filters: {'is_sales_item': 1, 'customer': cur_frm.doc.customer, 'has_variants': 0}
                }
            });
        }
    }
})