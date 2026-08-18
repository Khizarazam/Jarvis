"""
meta_ads.py
-----------
Thin wrapper around Meta's Marketing (Graph) API to turn an ad set ON or OFF.

Requires:
- A Meta access token with the "ads_management" permission
- The numeric ID of an ad set that already exists in Ads Manager

This does NOT create ads or campaigns from scratch — it assumes you already
built the campaign/ad set in Ads Manager (in a paused state) and just want
the ON/OFF switch to be automatic at a scheduled time.
"""

import requests

GRAPH_API_VERSION = "v19.0"


def _graph_url(ad_set_id):
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ad_set_id}"


def set_ad_set_status(ad_set_id, access_token, status):
    """
    status must be "ACTIVE" or "PAUSED"
    Returns (success: bool, message: str)
    """
    if status not in ("ACTIVE", "PAUSED"):
        return False, f"Invalid status: {status}"

    url = _graph_url(ad_set_id)
    params = {"status": status, "access_token": access_token}

    try:
        resp = requests.post(url, params=params, timeout=15)
        data = resp.json()
        if resp.status_code == 200 and data.get("success", True):
            return True, f"Ad set {ad_set_id} set to {status}."
        else:
            error_msg = data.get("error", {}).get("message", str(data))
            return False, f"Meta API error: {error_msg}"
    except requests.RequestException as e:
        return False, f"Network error contacting Meta API: {e}"


def activate_ad_set(ad_set_id, access_token):
    return set_ad_set_status(ad_set_id, access_token, "ACTIVE")


def pause_ad_set(ad_set_id, access_token):
    return set_ad_set_status(ad_set_id, access_token, "PAUSED")


def get_ad_set_status(ad_set_id, access_token):
    """Check current status of an ad set. Returns status string or None on failure."""
    url = _graph_url(ad_set_id)
    params = {"fields": "status,name", "access_token": access_token}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if resp.status_code == 200:
            return data.get("status")
        return None
    except requests.RequestException:
        return None
