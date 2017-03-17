# -*- coding: utf-8 -*-
# Copyright (c) 2015, DigiThinkIT, Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _dict
from frappe.model.document import Document
from frappe.utils import get_url, call_hook_method, cint, flt
from urllib import urlencode
from frappe.integration_broker.doctype.integration_service.integration_service import IntegrationService, get_integration_controller

class GatewaySelectorSettings(IntegrationService):
    service_name = "Gateway Selector"

    def validate(self):
        pass

    def on_update(self):
        pass

    def enable(self):
        call_hook_method("payment_gateway_enabled", gateway=self.service_name)

    def validate_transaction_currency(self, currency):
        for gateway in self.gateways:
            controller = get_integration_controller(gateway.service)
            controller.validate_transaction_currency(currency)

    def get_payment_url(self, **kwargs):
        proxy = self.build_proxy(**kwargs)
        url = "./integrations/gateway_selector/{0}"
        return get_url(url.format(proxy.get("name" )))

    def build_proxy(self, **kwargs):
        data = {
            "doctype": "Gateway Selector Proxy"
        }
        data.update(kwargs)
        proxy = frappe.get_doc(data)

        proxy.flags.ignore_permissions = 1
        proxy.insert()

        return proxy


@frappe.whitelist()
def get_service_details():
    return """
        <div>
            <p>    This service is a proxy gateway which allows your users
                to select their own payment gateway from a list of available
                preconfigured gateways.
            </p>
            <p> Click the settings button above to configure available gateways</p>
        </div>
    """

def get_awc_gateway_form():
    """This is the Gateway Selector embed form used by awc to embed itself on
    the cart's frontend"""

    context = _dict({
        "source": "templates/includes/integrations/gateway_selector/embed.html",
        "submit_source": "templates/includes/integrations/gateway_selector/submit.html"
    })

    build_embed_context(context)

    return {
        "form": frappe.render_template(context.source, context),
        "submit": frappe.render_template(context.submit_source, context),
        "styles": context["gateway_styles"],
        "scripts": context["gateway_scripts"],
        "js_api_factory": "frappe.integration_service.gateway_selector_gateway"
    }

def is_gateway_embedable(name):
    """Returns True if the the gateway supports get_embed_form api"""

    controller = get_integration_controller(name)
    return hasattr(controller, "is_embedable") and controller.is_embedable

def get_gateway_embed_form(name):
    """Gets the gateway's embedable form information"""

    controller = get_integration_controller(name)
    return controller.get_embed_form()

@frappe.whitelist(allow_guest=True)
def get_url_from_gateway(gateway, data):
    """Gets the gateway url when deferring gateways that can not be embeded"""

    gateway_selector = get_integration_controller("Gateway Selector")

    for g in gateway_selector.gateways:
        if g.service.replace(' ', '_').lower() == gateway:
            gateway_name = g.service
            break
    else:
        gateway_name = None

    controller = get_integration_controller(gateway_name)

    return controller.get_payment_url(**data)

@frappe.whitelist(allow_guest=True)
def get_gateways():
    """Gets a list of gateways that can be selected and their embedding information"""

    gateway_selector = get_integration_controller("Gateway Selector")
    gateways = []
    for gateway in gateway_selector.gateways:
        payload = {
            "name": gateway.service.replace(' ', '_').lower(),
            "data": { key: gateway.get(key) for key in ['label', 'icon', 'service', 'is_default'] },
            "is_embedable": is_gateway_embedable(gateway.service)
        }

        if payload["is_embedable"]:
            payload["embed_form"] = get_gateway_embed_form(gateway.service)

        gateways.append(payload)

    return gateways

def build_embed_context(context):
    """Convenience method that adds gateway information for a page's context"""

    context["data"] = {}
    gateways = get_gateways()

    context["gateway_scripts"] = ['/assets/js/gateway_selector_embed.js']
    context["gateway_styles"] = ['/assets/css/gateway_selector_embed.css']
    context["gateways"] = gateways

    for gateway in gateways:
        if gateway.get('embed_form'):
            context["gateway_scripts"].append(gateway.get('embed_form').get("script_url"))
            context["gateway_styles"].append(gateway.get('embed_form').get("style_url"))