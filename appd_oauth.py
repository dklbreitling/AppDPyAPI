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

    @dataclass
    class AppDOauthToken:
        token: str | None = None
        expiry: int | None = None
        _lock: threading.Lock = threading.Lock()

        def lock(self): self._lock.acquire(blocking=True, timeout=5)
        def unlock(self): self._lock.release()

        def __getitem__(self, item: slice) -> str:
            return self.token[item] if self.token is not None else ""

        def __bool__(self): return bool(self.token)
        def __repr__(self): return str(self.token)

    def __init__(self, token_url: str, client_id: str, client_secret: str,
                 config: AppDOAuthConfig = AppDOAuthConfig()):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_lock = threading.Lock()

        # Private
        self._config = config
        self._token = self.AppDOauthToken()
        self._timer: threading.Timer | None = None

    def get_token(self) -> AppDOauthToken:
        """Get access token.

        Returns:
            AppDOAuthToken: Acccess token.
        """
        if not self._token:
            self._refresh_token()

        return self._token

    def lock_token(self): self._token.lock()

    def unlock_token(self): self._token.unlock()

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

        self.lock_token()
        self._token.token = res[self._config.TOKEN_KEY]
        self._token.expiry = int(res[self._config.EXPIRY_KEY])
        self.unlock_token()

        if self._config.keep_refreshing_token:
            self._set_refresh_token_timer(self._token.expiry)

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
