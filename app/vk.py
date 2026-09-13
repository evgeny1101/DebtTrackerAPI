import json

import httpx

from app.config import VK_CLIENT_ID

VK_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
VK_USER_INFO_URL = "https://id.vk.ru/oauth2/user_info"

_TIMEOUT_SECONDS = 10.0


class VKAuthError(Exception):
    pass


class VKTransientError(VKAuthError):
    pass


def _parse_json(resp: httpx.Response) -> dict:
    try:
        payload = resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise VKAuthError("VK returned a malformed (non-JSON) response") from exc

    if not isinstance(payload, dict):
        raise VKAuthError("VK returned a malformed response body")
    return payload


def exchange_code(
    code: str,
    redirect_uri: str,
    code_verifier: str,
    device_id: str,
    state: str | None = None,
) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "client_id": VK_CLIENT_ID,
        "device_id": device_id,
    }
    if state:
        data["state"] = state

    try:
        resp = httpx.post(VK_TOKEN_URL, data=data, timeout=_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise VKTransientError(f"VK token request failed: {exc}") from exc

    if resp.status_code >= 500:
        raise VKTransientError(f"VK token exchange returned HTTP {resp.status_code}")

    payload = _parse_json(resp)
    if resp.status_code != 200:
        error = "unknown_error"
        if isinstance(payload.get("error"), str):
            error = payload["error"]
        raise VKAuthError(f"VK token exchange failed: {error}")

    access_token = payload.get("access_token")
    user_id = payload.get("user_id")
    if not isinstance(access_token, str) or not access_token or user_id is None:
        raise VKAuthError("VK token exchange response is missing access_token or user_id")

    return payload


def get_user_info(access_token: str) -> dict:
    data = {
        "client_id": VK_CLIENT_ID,
        "access_token": access_token,
    }

    try:
        resp = httpx.post(VK_USER_INFO_URL, data=data, timeout=_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise VKTransientError(f"VK user_info request failed: {exc}") from exc

    if resp.status_code >= 500:
        raise VKTransientError(f"VK user_info returned HTTP {resp.status_code}")

    payload = _parse_json(resp)
    if resp.status_code != 200:
        error = "unknown_error"
        if isinstance(payload.get("error"), str):
            error = payload["error"]
        raise VKAuthError(f"VK user_info failed: {error}")

    user = payload.get("user")
    if not isinstance(user, dict):
        raise VKAuthError("VK user_info response is missing a valid user object")

    for field in ("user_id", "first_name", "last_name"):
        value = user.get(field)
        if value is not None and not isinstance(value, str):
            raise VKAuthError(f"VK user profile field '{field}' has an invalid type")
    if user.get("email") is not None and not isinstance(user.get("email"), str):
        raise VKAuthError("VK user profile field 'email' has an invalid type")

    return user
