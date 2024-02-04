import logging
import requests
import threading
import time

from dataclasses import dataclass

from ._common import AppDException


@dataclass
class AppDOAuthConfig:
    CONTROLLER_BASE_URL: str
    CLIENT_ID: str
    CLIENT_SECRET: str

    keep_refreshing_token: bool = True
    TOKEN_KEY: str = "access_token"
    EXPIRY_KEY: str = "expires_in"
    OAUTH_ENDPOINT: str = "/controller/api/oauth/access_token"


class AppDOAuthException(AppDException):
    pass


class AppDOAuthTokenKeyNotFound(AppDOAuthException):
    pass


class AppDOAuthExpiryKeyNotFound(AppDOAuthException):
    pass


class AppDOAuthAuthorizationFailed(AppDOAuthException):
    pass


class AppDOAuth:

    @dataclass
    class AppDOauthToken:
        token: str | None = None
        expiry: int | None = None
        _lock: threading.Lock = threading.Lock()

        def lock(self):
            self._lock.acquire(blocking=True, timeout=5)

        def unlock(self):
            self._lock.release()

        def __getitem__(self, item: slice) -> str:
            return self.token[item] if self.token is not None else ""

        def __bool__(self):
            return bool(self.token)

        def __repr__(self):
            return str(self.token)

    def __init__(self, controller_base_url: str, client_id: str, client_secret: str):
        self._config = AppDOAuthConfig(controller_base_url, client_id, client_secret)
        self._token = self.AppDOauthToken()
        self._token_lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._refresh_token()

    def get_token(self) -> AppDOauthToken:
        """Get access token.

        Returns:
            AppDOAuthToken: Acccess token.
        """
        if not self._token:
            self._refresh_token()

        return self._token

    def lock_token(self):
        self._token.lock()

    def unlock_token(self):
        self._token.unlock()

    def stop_refreshing_token(self) -> None:
        """Stop refreshing the access token."""
        self._config.keep_refreshing_token = False
        if self._timer:
            self._timer.cancel()

    def _refresh_token(self) -> None:
        """Private method.

        Requests a new token and stores it in `self._token`.

        Side Effect: 
            Sets timer to refresh the token if `self._config.keep_refreshing_token` is set to `True`.
        """
        oauth_uri = f"{self._config.CONTROLLER_BASE_URL}{self._config.OAUTH_ENDPOINT}"
        request_data = f"grant_type=client_credentials&client_id={self._config.CLIENT_ID}&client_secret={self._config.CLIENT_SECRET}"
        response = requests.post(oauth_uri, data=request_data.encode())
        logging.debug(
            f"Requested new token from {oauth_uri} with data {request_data}, response status code {response.status_code}."
        )

        if response.status_code != 200:
            raise AppDOAuthAuthorizationFailed(
                f"Authorization failed.Received status code {response.status_code}.")

        parsed_response: dict[str, str] = response.json()
        logging.debug(f"Requested new token, parsed response: {parsed_response}")

        if self._config.TOKEN_KEY not in parsed_response:
            raise AppDOAuthTokenKeyNotFound(
                f"Specified token key ({self._config.TOKEN_KEY}) not in response.")

        if self._config.EXPIRY_KEY not in parsed_response:
            raise AppDOAuthExpiryKeyNotFound(
                f"Specified expiry key ({self._config.EXPIRY_KEY}) not in response.")

        self.lock_token()
        self._token.token = parsed_response[self._config.TOKEN_KEY]
        self._token.expiry = int(time.time() + int(parsed_response[self._config.EXPIRY_KEY]) - 1)
        self.unlock_token()

        if self._config.keep_refreshing_token:
            self._set_refresh_token_timer(int(parsed_response[self._config.EXPIRY_KEY]))

    def _set_refresh_token_timer(self, expiry: int):
        """Private method.

        Starts a timer to refresh the access token.

        Args:
            expiry (int): Seconds until access token expires.
        """
        interval = expiry - 5 if expiry > 5 else 1
        self._timer = threading.Timer(interval, self._refresh_token)
        self._timer.daemon = True
        self._timer.start()
