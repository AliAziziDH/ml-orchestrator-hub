# Cloudflare DNS Setup for Orchestra Webhook Gateway

To direct live email traffic to our setup, please configure your Cloudflare DNS records as follows:

## 1. Subdomain for the Gateway (API)
Create an A record to point `api.mrsaz7.com` to your GCP VM's public IP address.

*   **Type**: `A`
*   **Name**: `api`
*   **IPv4 address**: `<Your_GCP_VM_Public_IP>`
*   **Proxy status**: Proxied (Orange cloud) - *Crucial for Cloudflare SSL to work.*

*Note: The Nginx configuration relies on Cloudflare Origin SSL certificates. Make sure you generate these in Cloudflare (SSL/TLS -> Origin Server) and save them to `/etc/ssl/certs/cloudflare_origin.pem` and `/etc/ssl/private/cloudflare_origin.key` on your GCP VM.*

## 2. Inbound Email Setup (SendGrid)
We need to direct email traffic intended for `spark.mrsaz7.com` to SendGrid so their Parse Webhook can forward it to our API.

*   **Type**: `MX`
*   **Name**: `spark`
*   **Mail server**: `mx.sendgrid.net`
*   **TTL**: Auto
*   **Priority**: 10

## 3. SendGrid Inbound Parse Configuration
After updating the MX record in Cloudflare:

1.  Log in to your SendGrid account.
2.  Navigate to **Settings** -> **Inbound Parse**.
3.  Click **Add Host & URL**.
4.  **Domain**: Select/Enter `spark.mrsaz7.com`
5.  **Destination URL**: `https://api.mrsaz7.com/v1/webhook/email`
6.  Leave **POST the raw, full MIME message** unchecked (our gateway expects SendGrid's parsed JSON/Form Data format).
7.  Click **Add**.

Now, when a user replies to an email originating from the gateway (e.g., replying to `auth-id@spark.mrsaz7.com`), it will be routed to SendGrid -> processed -> POSTed to `https://api.mrsaz7.com/v1/webhook/email` -> accepted by Nginx -> forwarded to the local FastAPI app on port 8000!
