
# AppDPyAPI

This is an unofficial Python SDK for the AppDynamics API.

## Getting Started

### Requirements

- An [AppDynamics API Client](https://docs.appdynamics.com/appd/24.x/latest/en/extend-appdynamics/appdynamics-apis/api-clients)
- Python 3.10 or higher with the requests library (see [the requirements file](requirements.txt))

### Installation

Install using pip:
```
pip install git+https://github.com/dklbreitling/AppDPyAPI.git
```

### Usage

This is a basic example of how to use the SDK in a Python application:

```python
import AppDPyAPI

if __name__ == "__main__":
    base_url = "your.appd-controller.com"
    client_id = "your_api_client_id"
    client_secret = "your_api_client_secret"

    controller = AppDPyAPI.AppDController(base_url, client_id, client_secret)

    try:
        apps = controller.get_applications()
        app = controller.get_application(apps[0]["name"])
        print(f"Some app details: {app}")
        bts = controller.get_business_transactions(app["name"])
        if len(bts) > 0:
            print(f"A business transaction: {bts[0]}")
        else:
            print(f"There are no business transactions in the application {app['name']}.")
        auto_rules = controller.get_custom_transaction_detection_rules(int(app["id"]))
        custom_rules = controller.get_auto_transaction_detection_rules(int(app["id"]))
        print("Got some rules, but don't want to print XML.")

    except AppDPyAPI.AppDException as e:
        print(f"Something went wrong: {e}")

```

## API Documentation

The documentation for the AppDynamics API is available [here](https://docs.appdynamics.com/appd/latest).

## License
See the [license file](LICENSE.txt).
