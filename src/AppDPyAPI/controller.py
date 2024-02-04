import requests

from ._common import AppDException
from .oauth import AppDOAuth


class AppDController:
    """AppDynamics controller, authorized using OAuth. Requires an API client.
    
    Methods:
        get(self, uri, **kwargs): Wrapper for `requests.get`, automatically adding Bearer token.
        get_applications(self): Request all applications from the controller, returning parsed JSON.
        get_application(self, application_name): Get an application by name, returning parsed JSON.
        get_business_transactions(self, application_name): Get all business transactions for an app.
        get_custom_transaction_detection_rules(self, application_id): Get all custom detection rules.
        get_auto_transaction_detection_rules(self, application_id): Get all automatic detection rules.
    """

    def __init__(self, controller_base_url: str, client_id: str, client_secret: str):

        self.CONTROLLER_BASE_URL = controller_base_url
        self.auth: AppDOAuth = AppDOAuth(controller_base_url, client_id, client_secret)

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

        kwargs = self._safe_add_to_kwargs("headers", "Authorization", f"Bearer {self.auth.get_token()}",
                                          **kwargs)
        kwargs = self._safe_add_to_kwargs("params", "output", "JSON", **kwargs)
        res = requests.get(uri, **kwargs)  # type: ignore

        self.auth.unlock_token()

        return res

    def get_applications(self) -> list[dict[str, str]]:
        """Request all applications from the controller, formatted in JSON.

        Returns:
            list[dict[str, str]]: The parsed API response.
        """
        uri = self._get_uri("/controller/rest/applications")
        res = self._get_or_raise(uri, f"applications")
        return res.json()

    def get_application(self, application_name: str) -> dict[str, str]:
        """Request an application from the controller by application name, formatted in JSON.

        Args:
            application_name (str): The application name.
            
        Returns:
            list[dict[str, str]]: The parsed API response.
        """
        uri = self._get_uri(f"/controller/rest/applications/{application_name}")
        res = self._get_or_raise(uri, f"application {application_name}")
        return res.json()[0]

    def get_business_transactions(self, application_name: str) -> list[dict[str, str]]:
        """Request all business transactions for an application by application name, formatted in JSON.

        Args:
            application_name (str): The application name.
            
        Returns:
            list[dict[str, str]]: The parsed API response.
        """
        uri = self._get_uri(f"/controller/rest/applications/{application_name}/business-transactions")
        res = self._get_or_raise(uri, "business transactions")
        return res.json()

    def get_custom_transaction_detection_rules(self, application_id: int) -> str:
        """Request all custom transaction detection rules for an application by application ID,
        formatted in XML.
        
        Args:
            application_id (int): The application ID.

        Returns:
            str: The XML string of transaction detection rules.
        """
        uri = self._get_uri(f"/controller/transactiondetection/{application_id}/custom")
        res = self._get_or_raise(uri, "custom detection rules")
        return res.text

    def get_auto_transaction_detection_rules(self, application_id: int) -> str:
        """Request all automatic transaction detection rules for an application by application ID,
        formatted in XML.

        Args:
            application_id (int): The application ID.

        Returns:
            str: The XML string of transaction detection rules.
        """
        uri = self._get_uri(f"/controller/transactiondetection/{application_id}/auto")
        res = self._get_or_raise(uri, "auto detection rules")
        return res.text

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

    def _get_or_raise(self,
                      uri: str,
                      object_name: str,
                      expected_status_code: int = 200,
                      **kwargs: dict[str, str]):
        """Private method.
        
        Supports passing `**kwargs` that are then passed on to `get`.

        Args:
            uri (str): The URI to GET.
            object_name (str): String describing what is being fetched, e.g. "transaction detection rules".
            expected_status_code (int, optional): Expected status code of the response. Defaults to 200.

        Raises:
            AppDException: Raised if the response's status code is not equal to the expected status code.

        Returns:
            request.Response: The API response.
        """
        res = self.get(uri, **kwargs)
        if res.status_code != expected_status_code:
            raise AppDException(self._could_not_get_exception_msg(object_name, res.status_code))
        return res

    def _could_not_get_exception_msg(self, object_name: str, status_code: int):
        return f"Could not get {object_name}, received status code {status_code}"

    def _get_uri(self, endpoint: str) -> str:
        """Private method.
        
        Get the URI for an endpoint.

        Args:
            endpoint (str): The endpoint to get the URI for.

        Returns:
            str: The URI.
        """
        return f"{self.CONTROLLER_BASE_URL}{endpoint}"
