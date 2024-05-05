import frappe
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from india_compliance.gst_india.utils import (
    
    get_place_of_supply,

    is_overseas_doc,
   
)
from india_compliance.gst_india.constants import (
  
    STATE_NUMBERS
)

@frappe.whitelist()
def get_gst_details(party_details, doctype, company, *, update_place_of_supply=True):
    """
    This function does not check for permissions since it returns insensitive data
    based on already sensitive input (party details)

    Data returned:
     - place of supply (based on address name in party_details)
     - tax template
     - taxes in the tax template
    """

    is_sales_transaction = 1
    party_details = frappe.parse_json(party_details)
    gst_details = frappe._dict()

    party_address_field = (
        "customer_address" if is_sales_transaction else "supplier_address"
    )
    if not party_details.get(party_address_field):
        party_gst_details = get_party_gst_details(party_details, is_sales_transaction)

        # updating party details to get correct place of supply
        if party_gst_details:
            party_details.update(party_gst_details)
            gst_details.update(party_gst_details)
    
    gst_details.place_of_supply = (
        party_details.place_of_supply
        if (not update_place_of_supply and party_details.place_of_supply)
        else get_place_of_supply_nanak(party_details)
    )

    if is_sales_transaction:
        source_gstin = party_details.company_gstin
        destination_gstin = party_details.billing_address_gstin
    else:
        source_gstin = party_details.supplier_gstin
        destination_gstin = party_details.company_gstin

    # set is_reverse_charge as per party_gst_details if not set
    if not is_sales_transaction and "is_reverse_charge" not in party_details:
        is_reverse_charge = frappe.db.get_value(
            "Supplier",
            party_details.supplier,
            "is_reverse_charge_applicable as is_reverse_charge",
            as_dict=True,
        )

        if is_reverse_charge:
            party_details.update(is_reverse_charge)
            gst_details.update(is_reverse_charge)

    if doctype == "Payment Entry":
        return gst_details

    if (
        (destination_gstin and destination_gstin == source_gstin)  # Internal transfer
        or (
            is_sales_transaction
            and (
                is_export_without_payment_of_gst(party_details)
                or party_details.is_reverse_charge
            )
        )
        or (
            not is_sales_transaction
            and (
                party_details.gst_category == "Registered Composition"
                or (
                    not party_details.is_reverse_charge
                    and not party_details.supplier_gstin
                )
            )
        )
    ):
        # GST Not Applicable
        gst_details.taxes_and_charges = ""
        gst_details.taxes = []
        return gst_details

    master_doctype = (
        "Sales Taxes and Charges Template"
        if is_sales_transaction
        else "Purchase Taxes and Charges Template"
    )

    tax_template_by_category = get_tax_template_based_on_category(
        master_doctype, company, party_details
    )

    if tax_template_by_category:
        gst_details.taxes_and_charges = tax_template_by_category
        gst_details.taxes = get_taxes_and_charges(
            master_doctype, tax_template_by_category
        )
        return gst_details

    if not gst_details.place_of_supply or not party_details.company_gstin:
        return gst_details

    default_tax = get_tax_template(
        master_doctype,
        company,
        is_inter_state_supply(
            party_details.copy().update(
                doctype=doctype,
                place_of_supply=gst_details.place_of_supply,
            )
        ),
        party_details.company_gstin[:2],
        party_details.is_reverse_charge,
    )
    if default_tax:
        
        gst_details.taxes_and_charges = default_tax
        gst_details.taxes = get_taxes_and_charges(master_doctype, default_tax)

    return gst_details

def get_party_gst_details(party_details, is_sales_transaction):
    """fetch GSTIN and GST category from party"""

    party_type = "Customer" if is_sales_transaction else "Supplier"
    gstin_fieldname = (
        "billing_address_gstin" if is_sales_transaction else "supplier_gstin"
    )

    if not (party := party_details.get(party_type.lower())) or not isinstance(
        party, str
    ):
        return

    return frappe.db.get_value(
        party_type,
        party,
        ("gst_category", f"gstin as {gstin_fieldname}"),
        as_dict=True,
    )

def is_export_without_payment_of_gst(doc):
    return is_overseas_doc(doc) and not doc.is_export_with_gst

def get_tax_template_based_on_category(master_doctype, company, party_details):
    if not party_details.tax_category:
        return

    default_tax = frappe.db.get_value(
        master_doctype,
        {"company": company, "tax_category": party_details.tax_category},
        "name",
    )

    return default_tax

def get_tax_template(
    master_doctype, company, is_inter_state, state_code, is_reverse_charge
):
   
    tax_categories = frappe.get_all(
        "Tax Category",
        fields=["name", "is_inter_state", "gst_state"],
        filters={
            "is_inter_state": 1 if is_inter_state else 0,
            "is_reverse_charge": 1 if is_reverse_charge else 0,
            "disabled": 0,
        },
    )

    default_tax = ""

    for tax_category in tax_categories:
        
       
        if STATE_NUMBERS.get(tax_category.gst_state) == state_code or (
            not default_tax and not tax_category.gst_state
        ):
            
            default_tax = frappe.db.get_value(
                master_doctype,
                {"company": company, "disabled": 0, "tax_category": tax_category.name},
                "name",
            )
    return default_tax

def is_inter_state_supply(doc):
    
    return doc.gst_category == "SEZ" or (
        doc.place_of_supply[:2] != get_source_state_code(doc)
    )

def get_source_state_code(doc):
    """
    Get the state code of the state from which goods / services are being supplied.
    Logic opposite to that of utils.get_place_of_supply
    """

    if doc.doctype in "Nanak Pick List" or doc.doctype == "Payment Entry":
        return doc.company_gstin[:2]

    if doc.gst_category == "Overseas":
        return "96"

    if doc.gst_category == "Unregistered" and doc.supplier_address:
        return frappe.db.get_value(
            "Address",
            doc.supplier_address,
            "gst_state_number",
        )

    return (doc.supplier_gstin or doc.company_gstin)[:2]

def get_place_of_supply_nanak(party_details):
    party_gstin = party_details.billing_address_gstin or party_details.company_gstin

    if not party_gstin:
        return

    state_code = party_gstin[:2]
    

    if state := get_state(state_code):
        return f"{state_code}-{state}"
    
def get_state(state_number):
    """Get state from State Number"""

    state_number = str(state_number).zfill(2)

    for state, code in STATE_NUMBERS.items():
        if code == state_number:
            return state