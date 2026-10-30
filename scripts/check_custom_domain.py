"""Independent verification of the public custom domain, not the legacy Pages URL."""
from __future__ import annotations

import json
import socket
import ssl
import urllib.request
from urllib.parse import urlparse

DOMAIN = "thefinancialedition.com"
HOSTS = (DOMAIN, "www." + DOMAIN)
GITHUB_IPV4 = {"185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"}


def check(host):
    data = {"host": host}
    try:
        ips = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        data["dns_addresses"] = ips
        if host == DOMAIN:
            data["ipv4_on_github"] = bool(GITHUB_IPV4.intersection(ips))
    except Exception as error:
        data["dns_error"] = str(error)
        return data, False

    try:
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as tls:
                certificate = tls.getpeercert()
                data["tls_version"] = tls.version()
                data["certificate_expires"] = certificate.get("notAfter", "unknown")
                data["certificate_names"] = [name for kind, name in certificate.get("subjectAltName", []) if kind == "DNS"][:12]
    except Exception as error:
        data["https_error"] = str(error)
        return data, False

    try:
        req = urllib.request.Request("https://" + host + "/", headers={"User-Agent": "FinancialEdition-DomainHealth/1.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data["https_status"] = response.status
            data["https_final_url"] = response.url
            body = response.read(150000).decode("utf-8", errors="replace")
            data["publication_visible"] = "THE FINANCIAL EDITION" in body
            data["https_on_custom_domain"] = urlparse(response.url).hostname in HOSTS
    except Exception as error:
        data["https_response_error"] = str(error)
        return data, False

    try:
        req = urllib.request.Request("http://" + host + "/", headers={"User-Agent": "FinancialEdition-DomainHealth/1.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data["http_final_url"] = response.url
            data["http_upgrades_to_https"] = urlparse(response.url).scheme == "https"
    except Exception as error:
        data["http_redirect_error"] = str(error)
        data["http_upgrades_to_https"] = False

    return data, bool(data["publication_visible"] and data["https_on_custom_domain"] and data["http_upgrades_to_https"])


def main():
    results = []
    healthy = True
    for host in HOSTS:
        result, good = check(host)
        results.append(result)
        healthy = healthy and good
    print("CUSTOM_DOMAIN_HTTPS_DIAGNOSTIC:", json.dumps({"healthy": healthy, "results": results}, sort_keys=True))
    if not healthy:
        raise SystemExit("Custom-domain HTTPS / redirects not yet verified; see diagnostic above.")


if __name__ == "__main__":
    main()
