from appd_oauth import *
import requests

from dataclasses import dataclass


@dataclass
class AppDController:
    CONTROLLER_BASE_URL: str
    auth: AppDOAuth

    def get_uri(self, endpoint: str) -> str:
        """Get the URI for an endpoint.

        Args:
            endpoint (str): The endpoint to get the URI for.

        Returns:
            str: The URI.
        """
        return f"{self.CONTROLLER_BASE_URL}{endpoint}"

    def get(self, uri: str, **kwargs: dict[str, str]) -> requests.Response:
        """Wrapper for `requests.get`.

        Automatically adds `auth`'s `AppDOAuthToken` as Bearer token in authorization header in a thread-safe manner,
        unless a different authorization header is passed in `**kwargs`.

        Adds `output=JSON` parameter unless a different output parameter is passed in `**kwargs`.

        Args:
            uri (str): The URI to `GET`.
            **kwargs: See `requests.get`. 

        Returns:
            requests.Response: The API response.
        """

        self.auth.lock_token()

        kwargs = self._safe_add_to_kwargs(
            "headers", "Authorization", f"Bearer {self.auth.get_token()}", **kwargs)
        kwargs = self._safe_add_to_kwargs("params", "output", "JSON", **kwargs)
        res = requests.get(uri, **kwargs)  # type: ignore

        self.auth.unlock_token()

        return res

    def get_applications(self) -> requests.Response:
        """Request applications from the controller, formatted in JSON.

        Returns:
            requests.Response: The API response.
        """
        uri = self.get_uri("/controller/rest/applications")
        res = self.get(uri)
        return res

    def get_application(self, application_name: str) -> requests.Response:
        """Request applications from the controller, formatted in JSON.

        Returns:
            requests.Response: The API response.
        """
        uri = self.get_uri(f"/controller/rest/applications/{application_name}")
        res = self.get(uri)
        return res

    def get_business_transactions(self, application_name: str) -> requests.Response:
        uri = self.get_uri(
            f"/controller/rest/applications/{application_name}/business-transactions")
        res = self.get(uri)
        return res

    def get_custom_transaction_detection_rules(self, application_id: int) -> requests.Response:
        uri = self.get_uri(
            f"/controller/transactiondetection/{application_id}/custom")
        res = self.get(uri)
        return res

    def get_auto_transaction_detection_rules(self, application_id: int) -> requests.Response:
        uri = self.get_uri(
            f"/controller/transactiondetection/{application_id}/auto")
        res = self.get(uri)
        return res

    def _safe_add_to_kwargs(self, parent_key: str, child_key: str, value: str, **kwargs: dict[str, str]) -> dict[str, dict[str, str]]:
        """Private Method. 

        Add `{child_key: value}` to `kwargs[parent_key]` unless present, return new kwargs.

        Example usage: 
            `kwargs = self._safe_add_to_kwargs("params", "output", "JSON", **kwargs)`
        """
        if parent_key not in kwargs:
            kwargs[parent_key] = {child_key: value}
        elif child_key not in kwargs[parent_key]:
            kwargs[parent_key][child_key] = value
        return kwargs
