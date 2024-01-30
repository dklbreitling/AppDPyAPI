import logging
import requests
import threading

from dataclasses import dataclass


@dataclass
class AppDOAuthConfig:
    keep_refreshing_token: bool = True
    TOKEN_KEY: str = "access_token"
    EXPIRY_KEY: str = "expires_in"


class AppDOAuthException(Exception):
    pass


class AppDOAuthTokenKeyNotFound(AppDOAuthException):
    pass


class AppDOAuthExpiryKeyNotFound(AppDOAuthException):
    pass


class AppDOAuth:
    def __init__(self, token_url: str, client_id: str, client_secret: str,
                 config: AppDOAuthConfig = AppDOAuthConfig()):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret

        # Private
        self._config = config
        self._token: str | None = None
        self._timer: threading.Timer | None = None

    def get_token(self) -> str:
        """Get access token.

        Returns:
            str: Acccess token.
        """
        return self._token if self._token else self._get_new_token()

    def stop_refreshing_token(self) -> None:
        """Stop refreshing the access token."""
        self._config.keep_refreshing_token = False
        if self._timer:
            self._timer.cancel()

    def _get_new_token(self) -> str:
        """Private method.

        Requests a new token, stores it in `self.token`, and returns it.

        Side Effect: 
            Sets timer to refresh the token if `self._config.keep_refreshing_token` is set to `True`.

        Returns:
            str: Newly requested access token.
        """
        req = f"grant_type=client_credentials&client_id={self.client_id}&client_secret={self.client_secret}"
        raw = req.encode()
        res: dict[str, str] = requests.post(self.token_url, data=raw).json()

        logging.debug(f"Requested new token, response: {res}")

        if self._config.TOKEN_KEY not in res:
            raise AppDOAuthTokenKeyNotFound(
                f"Specified token key ({self._config.TOKEN_KEY}) not in response.\nResponse body: {res}")

        if self._config.EXPIRY_KEY not in res:
            raise AppDOAuthExpiryKeyNotFound(
                f"Specified expiry key ({self._config.EXPIRY_KEY}) not in response.\nResponse body: {res}")

        self._token = res[self._config.TOKEN_KEY]
        expiry = int(res[self._config.EXPIRY_KEY])

        if self._config.keep_refreshing_token:
            self._set_refresh_token_timer(expiry)

        return self._token

    def _set_refresh_token_timer(self, expiry: int):
        """Private method.

        Starts a timer to refresh the access token.

        Args:
            expiry (int): Seconds until access token expires.
        """
        interval = expiry - 5 if expiry > 5 else 1
        self._timer = threading.Timer(interval, self._get_new_token)
        self._timer.daemon = True
        self._timer.start()
