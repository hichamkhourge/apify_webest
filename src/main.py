"""Apify Actor wrapper around the WEBESTIPTV trial automation.

Reads the Actor input, maps it onto the environment variables that
``webestiptv_automation`` reads at import time, runs the (synchronous,
Selenium-based) flow in a worker thread, and reports the result to the Apify
dataset / key-value store and, optionally, to a webhook callback.
"""
import asyncio
import os

from apify import Actor

# Maps Actor input keys -> the env vars webestiptv_automation reads at import.
# Only non-empty values are applied so the module's own defaults still win.
_ENV_MAP = {
    "twoCaptchaApiKey": "TWOCAPTCHA_API_KEY",
    "baseUrl": "WEBEST_BASE_URL",
    "emailBackend": "WEBEST_EMAIL_BACKEND",
    "maxAttempts": "WEBEST_MAX_ATTEMPTS",
    "useProxy": "WEBEST_USE_PROXY",
    "proxyProtocol": "WEBEST_PROXY_PROTOCOL",
    "proxyMaxTries": "WEBEST_PROXY_MAX_TRIES",
    "otpWaitSeconds": "WEBEST_OTP_WAIT",
    "credentialsWaitSeconds": "WEBEST_CREDENTIALS_WAIT",
    "requestTrial": "WEBEST_REQUEST_TRIAL",
    "fetchCredentials": "WEBEST_FETCH_CREDENTIALS",
    "iboPlayerCookie": "WEBEST_IBOPLAYER_COOKIE",
    "iboPlayerMacAddress": "WEBEST_IBOPLAYER_MAC_ADDRESS",
    "iboPlayerDeviceKey": "WEBEST_IBOPLAYER_DEVICE_KEY",
    "iboPlayerPlaylistUrlId": "WEBEST_IBOPLAYER_PLAYLIST_URL_ID",
    "iboPlayerPlaylistName": "WEBEST_IBOPLAYER_PLAYLIST_NAME",
}


def _apply_input_to_env(actor_input):
    """Translate Actor input into the env vars the automation module expects."""
    for key, env_name in _ENV_MAP.items():
        value = actor_input.get(key)
        if value not in (None, ""):
            os.environ[env_name] = str(value)

    if actor_input.get("iboPlayerEnabled"):
        os.environ["WEBEST_IBOPLAYER_ENABLED"] = "True"

    # Apify always runs headless and should never hang waiting for a browser.
    os.environ["HEADLESS"] = "True"
    os.environ["AUTO_EXIT"] = "True"
    # Apify containers can't write to /app; use a writable scratch dir for artifacts.
    os.environ.setdefault("IPTVV_DEBUG_DIR", "/tmp/webest-logs")


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        _apply_input_to_env(actor_input)

        user_id = actor_input.get("userId")
        callback_url = actor_input.get("callbackUrl")

        # Import only AFTER env vars are set: the module reads them at import time.
        import webestiptv_automation as bot
        from iptvvcanada_automation import send_webhook_callback

        try:
            Actor.log.info("Starting WEBESTIPTV trial automation...")
            result = await asyncio.to_thread(bot.run_automation)
        except bot.TrialFailedError as exc:
            await _report_failure(send_webhook_callback, callback_url, user_id, exc)
            await Actor.fail(status_message=f"TrialFailedError: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 - surface any failure to the run
            Actor.log.exception("Automation failed")
            await _report_failure(send_webhook_callback, callback_url, user_id, exc)
            await Actor.fail(status_message=f"Automation failed: {exc}")
            return

        Actor.log.info("Credentials extracted successfully")
        output = {"status": "success", **result}
        await Actor.push_data(output)
        await Actor.set_value("OUTPUT", output)

        if callback_url:
            await asyncio.to_thread(
                send_webhook_callback,
                callback_url,
                user_id,
                "success",
                result.get("username"),
                result.get("password"),
                result.get("host"),
                result.get("m3u_url"),
            )


async def _report_failure(send_webhook_callback, callback_url, user_id, exc):
    """Persist the failure to the dataset/KV store and fire the webhook."""
    output = {"status": "failed", "error": str(exc)}
    await Actor.push_data(output)
    await Actor.set_value("OUTPUT", output)
    if callback_url:
        await asyncio.to_thread(
            send_webhook_callback,
            callback_url,
            user_id,
            "failed",
            None,
            None,
            None,
            None,
            str(exc),
        )
