import httpx

from app.config import VK_CLIENT_ID

VK_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
VK_USER_INFO_URL = "https://id.vk.ru/oauth2/user_info"

_TIMEOUT_SECONDS = 10.0


class VKAuthError(Exception):
    pass


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
        raise VKAuthError(f"VK token request failed: {exc}") from exc

    payload = resp.json()
    if resp.status_code != 200 or "access_token" not in payload:
        error = payload.get("error", "unknown_error")
        raise VKAuthError(f"VK token exchange failed: {error}")

    return payload


def get_user_info(access_token: str) -> dict:
    data = {
        "client_id": VK_CLIENT_ID,
        "access_token": access_token,
    }

    try:
        resp = httpx.post(VK_USER_INFO_URL, data=data, timeout=_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise VKAuthError(f"VK user_info request failed: {exc}") from exc

    payload = resp.json()
    if resp.status_code != 200 or "user" not in payload:
        error = payload.get("error", "unknown_error")
        raise VKAuthError(f"VK user_info failed: {error}")

    return payload["user"]
