from typing import Any, Callable
import requests

from ._common import AppDException
from .oauth import AppDOAuth


class AppDController:
    """AppDynamics controller, authorized using OAuth. Requires an API client.
    """

    def __init__(self, controller_base_url: str, client_id: str, client_secret: str):
        self.CONTROLLER_BASE_URL = controller_base_url
        self.auth: AppDOAuth = AppDOAuth(controller_base_url, client_id, client_secret)

    def get(self, uri: str, **kwargs: dict[str, str]) -> requests.Response:
        """Wrapper for `requests.get`.

        Automatically adds `auth`'s `AppDOAuthToken` as Bearer token in authorization header in a thread-safe manner,
        unless a different authorization header is passed in `**kwargs`.

        To request JSON from the API (not supported on all endpoints, see docs), 
        add the `output=JSON` parameter to `**kwargs`.
        
        Example: `get(uri, params={"output": "JSON"})`.

        Args:
            uri (str): The URI to `GET`.
            **kwargs: See `requests.get`. 

        Returns:
            requests.Response: The API response.
        """

        return self.request("GET", uri, **kwargs)

    def post(self, uri: str, **kwargs: dict[str, str]) -> requests.Response:
        """Wrapper for `requests.post`.

        Automatically adds `auth`'s `AppDOAuthToken` as Bearer token in authorization header in a thread-safe manner,
        unless a different authorization header is passed in `**kwargs`.

        To request JSON from the API (not supported on all endpoints, see docs), 
        add the `output=JSON` parameter to `**kwargs`.
        
        Example: `post(uri, params={"output": "JSON"})`.

        Args:
            uri (str): The URI to `POST`.
            **kwargs: See `requests.post`. 

        Returns:
            requests.Response: The API response.
        """
        return self.request("POST", uri, **kwargs)

    def request(self, method: str, uri: str, **kwargs: dict[str, str]) -> requests.Response:
        """Wrapper for `requests.request`.
        
        Automatically adds `auth`'s `AppDOAuthToken` as Bearer token in authorization header in a thread-safe manner,
        unless a different authorization header is passed in `**kwargs`.
        
        To request JSON from the API (not supported on all endpoints, see docs), 
        add the `output=JSON` parameter to `**kwargs`.
        
        Example: `request("GET", uri, params={"output": "JSON"})`.

        Args:
            method (str): "GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", or "DELETE"
            uri (str): The URI to request.
            **kwargs: See `requests.request`. 

        Returns:
            requests.Response: The API response.
        """

        self.auth.lock_token()

        kwargs = self._safe_add_to_kwargs("headers", "Authorization", f"Bearer {self.auth.get_token()}",
                                          **kwargs)
        res = requests.request(method, uri, **kwargs)  # type: ignore

        self.auth.unlock_token()

        return res

    def _safe_add_to_kwargs(self, parent_key: str, child_key: str, value: str,
                            **kwargs: dict[str, str]) -> dict[str, dict[str, str]]:
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

    def _request_or_raise(self,
                          method: str,
                          uri: str,
                          object_name: str,
                          expected_status_code: int = 200,
                          **kwargs: dict[str, str]) -> requests.Response:
        """Private method.
        
        Supports passing `**kwargs` that are then passed on to `request`.

        Args:
            uri (str): The URI to request.
            object_name (str): String describing what is being fetched, e.g. "transaction detection rules".
            expected_status_code (int, optional): Expected status code of the response. Defaults to 200.

        Raises:
            AppDException: Raised if the response's status code is not equal to the expected status code.

        Returns:
            requests.Response: The API response.
        """
        res = self.request(method, uri, **kwargs)
        if res.status_code != expected_status_code:
            raise AppDException(self._could_not_get_exception_msg(object_name, res.status_code, res.text))
        return res

    def _get_or_raise(self,
                      uri: str,
                      object_name: str,
                      expected_status_code: int = 200,
                      **kwargs: dict[str, str]) -> requests.Response:
        """Private method. Convenience wrapper for `_request_or_raise`."""
        return self._request_or_raise("GET", uri, object_name, expected_status_code, **kwargs)

    def _could_not_get_exception_msg(self, object_name: str, status_code: int, res: str) -> str:
        return f"Could not get {object_name}, received status code {status_code}.\nRaw response: {res}"

    def _full_uri(self, endpoint: str) -> str:
        """Private method.
        
        Get the URI for an endpoint.

        Args:
            endpoint (str): The endpoint to get the URI for.

        Returns:
            str: The URI.
        """
        return f"{self.CONTROLLER_BASE_URL}{endpoint}"

    @staticmethod
    def __request_or_raise(method: str,
                           uri: str,
                           object_name: str,
                           json_decode: bool = True,
                           single_element: bool = False,
                           expected_status_code: int = 200,
                           **kwargs: dict[str, str]):
        """Private method.

        Uplink-style decorator for requests. Use like `_request_or_raise` but as decorator.

        URI and object name are expanded at runtime as `URITemplate`.

        Example usage:
            ```
            @__request_or_raise("GET",
                                        "/controller/rest/applications/{application_name}",
                                        "application {application_name}",
                                        headers={"myHeader": "value"})
            def get_application_decorated(application_name):
                \"""Get application by name.\"""
            ```
        """

        from inspect import signature
        from uritemplate import URITemplate

        def _inner_request_or_raise_decorator(
                func: Callable[[Any], Any]) -> Callable[[Any], str | list[dict[str, str]]]:
            """Handles function."""

            def __inner_request_or_raise_decorator(*args: list[Any]) -> str | list[dict[str, str]]:
                """Handles arguments passed to function."""
                self: AppDController = args[0]  # type: ignore

                bound_args = signature(func).bind(*args).arguments
                expanded_uri = URITemplate(self._full_uri(uri)).expand(bound_args)
                expanded_object_name = URITemplate(object_name).expand(bound_args)

                k = kwargs
                json = json_decode or single_element

                if json:
                    k = self._safe_add_to_kwargs("params", "output", "JSON", **k)

                res: requests.Response = self._request_or_raise(method, expanded_uri, expanded_object_name,
                                                                expected_status_code, **k)

                if json:
                    return res.json() if not single_element else res.json()[0]

                return res.text

            return __inner_request_or_raise_decorator

        return _inner_request_or_raise_decorator

    @__request_or_raise("GET", "/controller/rest/applications", "applications")
    def get_applications(self) -> list[dict[str, str]]:  # type: ignore
        """Request all applications from the controller, formatted in JSON.

        Returns:
            list[dict[str, str]]: The parsed API response.
        """

    @__request_or_raise("GET",
                        "/controller/rest/applications/{application_name}",
                        "application {application_name}",
                        single_element=True)  # type: ignore
    def get_application(self, application_name: str) -> dict[str, str]:  # type: ignore
        """Request an application from the controller by application name, formatted in JSON.

        Args:
            application_name (str): The application name.

        Returns:
            dict[str, str]: The parsed API response.
        """

    @__request_or_raise("GET", "/controller/rest/applications/{application_name}/business-transactions",
                        "business transaction for {application_name}")  # type: ignore
    def get_business_transactions(self, application_name: str) -> list[dict[str, str]]:  # type: ignore
        """Request all business transactions for an application by application name, formatted in JSON.

        Args:
            application_name (str): The application name.

        Returns:
            list[dict[str, str]]: The parsed API response.
        """

    @__request_or_raise("GET",
                        "/controller/transactiondetection/{application_id}/custom",
                        "custom detection rules for application with ID {application_id}",
                        json_decode=False)  # type: ignore
    def get_custom_transaction_detection_rules(self, application_id: int) -> str:  # type: ignore
        """Request all custom transaction detection rules for an application by application ID,
        formatted in XML.

        Args:
            application_id (int): The application ID.

        Returns:
            str: The XML string of transaction detection rules.
        """

    @__request_or_raise("GET",
                        "/controller/transactiondetection/{application_id}/auto",
                        "auto detection rules for application with ID {application_id}",
                        json_decode=False)  # type: ignore
    def get_auto_transaction_detection_rules(self, application_id: int) -> str:  # type: ignore
        """Request all automatic transaction detection rules for an application by application ID,
        formatted in XML.

        Args:
            application_id (int): The application ID.

        Returns:
            str: The XML string of transaction detection rules.
        """

    @__request_or_raise("GET", "/controller/mds/v1/license/rules", "license rules")
    def get_license_rules(self):
        """Requires Agent-Based Licensing (ABL). Get license rules."""

    def get_account_id(self) -> int:
        return int(
            self._get_or_raise(self._full_uri("/controller/api/accounts/myaccount"),
                               "account info",
                               params={
                                   "output": "json"
                               }).json()["id"])

    @__request_or_raise("GET", "/controller/licensing/v1/account/{accountId}/allocation",
                        "licensing allocations for account {accountId}")  #type: ignore
    def get_license_allocations(self, accountId: int):
        """Requires Infrastructure-Based Licensing (IBL). Retrieve all license allocations for account with ID `accountId`.

        Args:
            accountId (int): The account ID.

        Returns:
            list[dict[str, str | int | list[str]]]: The parsed API response.
        """

    @__request_or_raise(
        "GET", "/controller/licensing/v1/account/{accountId}/allocation?name={allocation_name}",
        "licensing allocations for account {accountId} for allocation {allocation_name}")  #type: ignore
    def get_license_allocation_by_name(self, accountId: int, allocation_name: str):
        """Requires Infrastructure-Based Licensing (IBL). Like `get_license_allocations`, but additionally filtered by allocation name."""

    @__request_or_raise(
        "GET", "/controller/licensing/v1/account/{accountId}/allocation?license-key={license_key}",
        "licensing allocations for account {accountId} for allocation {license_key}")  #type: ignore
    def get_license_allocation_by_license_key(self, accountId: int, license_key: str):
        """Requires Infrastructure-Based Licensing (IBL). Like `get_license_allocations`, but additionally filtered by license key."""

    @__request_or_raise("GET", "/controller/licensing/v1/account/{accountId}/allocation?tag={tag}",
                        "licensing allocations for account {accountId} for allocation {tag}")  #type: ignore
    def get_license_allocations_by_tag(self, accountId: int, tag: str):
        """Requires Infrastructure-Based Licensing (IBL). Like `get_license_allocations`, but additionally filtered by tag assocatied with allocations."""
