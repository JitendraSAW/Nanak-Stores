from . import __version__ as app_version

app_name = "nanak_customization"
app_title = "Nanak Customization"
app_publisher = "Raaj Tailor"
app_description = "Nanak Customization"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "tailorraj111@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/nanak_customization/css/nanak_customization.css"
# app_include_js = "/assets/nanak_customization/js/nanak_customization.js"

# include js, css files in header of web template
# web_include_css = "/assets/nanak_customization/css/nanak_customization.css"
# web_include_js = "/assets/nanak_customization/js/nanak_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "nanak_customization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

boot_session = "nanak_customization.nanak_customization.boot.set_bootinfo"
# include js in doctype views
doctype_js = {
    "Sales Order" : "custom_script/sales_order.js",
	"Quotation" : "custom_script/quotation.js",
    "Sales Invoice" : "custom_script/sales_invoice.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}
fixtures = [
	{"dt":"Custom Field", "filters": [["name", "in", ["Sales Invoice-picklist_reference","Stock Entry-picklist_item_reference","Stock Entry-nanak_pick_list","Warehouse-warehouse","Warehouse-is_reserve_warehouse","Sales Order Item-picked_qty","Sales Invoice Item-pick_list_details","Sales Invoice Item-nanak_pick_list","Customer Credit Limit-credit_days", "Customer-credit_limit_and_amount", "Customer-credit_days", "Customer-column_break_52", "Customer-credit_amount", "Customer Group-credit_limit_and_amount", "Customer Group-credit_days", "Customer Group-column_break_15", "Customer Group-credit_amount"]]]},
	{"dt":"Stock Entry Type", "filters": [["name", "in", ["Stock Reservation"]]]},
	{"dt":"Client Script", "filters": [["name", "in", ["Sales Invoice-Form"]]]}

	]
# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "nanak_customization.install.before_install"
# after_install = "nanak_customization.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "nanak_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }




# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
        "validate":"nanak_customization.nanak_customization.sales_invoice.validate",
		"on_submit": "nanak_customization.nanak_customization.sales_invoice.after_submit",
        "on_trash": "nanak_customization.nanak_customization.sales_invoice.on_trash",
	}
}

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"nanak_customization.tasks.all"
# 	],
# 	"daily": [
# 		"nanak_customization.tasks.daily"
# 	],
# 	"hourly": [
# 		"nanak_customization.tasks.hourly"
# 	],
# 	"weekly": [
# 		"nanak_customization.tasks.weekly"
# 	]
# 	"monthly": [
# 		"nanak_customization.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "nanak_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "nanak_customization.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "nanak_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"nanak_customization.auth.validate"
# ]

