import pytest
from unittest.mock import patch, MagicMock, call
import requests # Import for requests.exceptions.RequestException

from kite_wrapper.client import KiteClient
from kite_wrapper.config import KiteConfig
from kite_wrapper.exceptions import (KiteException, TokenException, GeneralException, InputException,
                                     DataException, NetworkException, PermissionException, OrderException)

# Minimal valid config for many tests
MOCK_API_KEY = "myapikey"
MOCK_API_SECRET = "myapisecret"
MOCK_ACCESS_TOKEN = "myaccesstoken"
MOCK_REQUEST_TOKEN = "myrequesttoken"

@pytest.fixture
def mock_kite_config():
    """Fixture to create a mock KiteConfig object (instance)."""
    config_instance = MagicMock(spec=KiteConfig)
    config_instance.get_api_key.return_value = MOCK_API_KEY
    config_instance.get_api_secret.return_value = MOCK_API_SECRET
    config_instance.get_access_token.return_value = MOCK_ACCESS_TOKEN
    config_instance.set_access_token = MagicMock()
    return config_instance

@pytest.fixture
@patch('kite_wrapper.client.KiteConfig')
@patch('kite_wrapper.client.KiteConnect')
def client_setup(MockKiteConnect_class, MockKiteConfig_class, mock_kite_config):
    MockKiteConfig_class.return_value = mock_kite_config

    mock_kc_instance = MagicMock()
    mock_kc_instance.login_url.return_value = f"https://kite.trade/connect/login?api_key={MOCK_API_KEY}&v=3"
    mock_kc_instance.generate_session.return_value = {"access_token": MOCK_ACCESS_TOKEN, "user_id": "AB1234"}
    MockKiteConnect_class.return_value = mock_kc_instance

    client = KiteClient(api_key=MOCK_API_KEY, api_secret=MOCK_API_SECRET, access_token=MOCK_ACCESS_TOKEN)

    # Mock the _request method directly on the client instance for endpoint tests
    client._request = MagicMock()

    client.mock_kc_instance = mock_kc_instance
    client.mock_config_instance = mock_kite_config
    client.MockKiteConnect_class = MockKiteConnect_class
    client.MockKiteConfig_class = MockKiteConfig_class
    return client


# Tests for basic client initialization and auth methods (existing tests)
def test_client_initialization_with_params(client_setup):
    client = client_setup
    assert client.api_key == MOCK_API_KEY
    assert client.access_token == MOCK_ACCESS_TOKEN
    assert client.mock_config_instance.get_api_key() == MOCK_API_KEY
    client.MockKiteConfig_class.assert_called_once_with(api_key=MOCK_API_KEY, api_secret=MOCK_API_SECRET, access_token=MOCK_ACCESS_TOKEN, config_path=None)
    client.MockKiteConnect_class.assert_called_once_with(api_key=MOCK_API_KEY, access_token=MOCK_ACCESS_TOKEN, proxies={}, root="https://api.kite.trade")
    assert client.kite_connect_client is not None
    client.mock_kc_instance.set_access_token.assert_called_once_with(MOCK_ACCESS_TOKEN)

@patch('kite_wrapper.client.KiteConfig')
@patch('kite_wrapper.client.KiteConnect')
def test_client_initialization_no_token_on_init(MockKiteConnect_class_direct, MockKiteConfig_class_direct):
    mock_config_instance = MagicMock(spec=KiteConfig)
    mock_config_instance.get_api_key.return_value = MOCK_API_KEY
    mock_config_instance.get_api_secret.return_value = MOCK_API_SECRET
    mock_config_instance.get_access_token.return_value = None
    MockKiteConfig_class_direct.return_value = mock_config_instance
    mock_kc_instance = MagicMock()
    MockKiteConnect_class_direct.return_value = mock_kc_instance
    # We need to ensure _request is not called during init for this specific test's client
    # So, we pass a real KiteClient, then mock its _request if needed, or ensure it's not used.
    # For this init test, _request is not involved.
    client = KiteClient(api_key=MOCK_API_KEY, api_secret=MOCK_API_SECRET)
    assert client.access_token is None
    MockKiteConnect_class_direct.assert_called_once_with(api_key=MOCK_API_KEY,access_token=None, proxies={},root="https://api.kite.trade")
    mock_kc_instance.set_access_token.assert_not_called()

def test_set_access_token(client_setup):
    client = client_setup
    new_token = "new_access_token_for_test"
    client.mock_kc_instance.set_access_token.reset_mock()
    client.set_access_token(new_token)
    assert client.access_token == new_token
    client.mock_config_instance.set_access_token.assert_called_with(new_token)
    client.mock_kc_instance.set_access_token.assert_called_once_with(new_token)
    assert client.session.headers["Authorization"] == f"token {MOCK_API_KEY}:{new_token}"

def test_login_url(client_setup):
    client = client_setup
    expected_url = f"https://kite.trade/connect/login?api_key={MOCK_API_KEY}&v=3"
    assert client.login_url() == expected_url
    client.mock_kc_instance.login_url.assert_called_once()

@patch('kite_wrapper.client.KiteConfig')
@patch('kite_wrapper.client.KiteConnect')
def test_login_url_no_kiteconnect_fallback(MockKiteConnect_class_direct, MockKiteConfig_class_direct, mock_kite_config):
    MockKiteConfig_class_direct.return_value = mock_kite_config
    MockKiteConnect_class_direct.side_effect = Exception("KC init failed")
    client = KiteClient(api_key=MOCK_API_KEY, api_secret=MOCK_API_SECRET)
    assert client.kite_connect_client is None
    expected_url = f"https://api.kite.trade/connect/login?api_key={MOCK_API_KEY}&v=3"
    assert client.login_url() == expected_url

def test_generate_session_success(client_setup):
    client = client_setup
    client.mock_config_instance.set_access_token.reset_mock()
    client.mock_kc_instance.set_access_token.reset_mock()
    session_data = client.generate_session(MOCK_REQUEST_TOKEN)
    assert session_data["access_token"] == MOCK_ACCESS_TOKEN
    assert client.access_token == MOCK_ACCESS_TOKEN
    client.mock_kc_instance.generate_session.assert_called_once_with(MOCK_REQUEST_TOKEN, api_secret=MOCK_API_SECRET)
    client.mock_config_instance.set_access_token.assert_called_once_with(MOCK_ACCESS_TOKEN)
    client.mock_kc_instance.set_access_token.assert_called_once_with(MOCK_ACCESS_TOKEN)

def test_generate_session_no_api_secret(client_setup):
    client = client_setup
    client.api_secret = None
    client.mock_kc_instance.generate_session.reset_mock()
    with pytest.raises(InputException) as excinfo:
        client.generate_session(MOCK_REQUEST_TOKEN)
    assert "API secret is required" in str(excinfo.value)
    client.mock_kc_instance.generate_session.assert_not_called()

def test_generate_session_kiteconnect_raises_token_exception(client_setup):
    client = client_setup
    error_message = "Invalid request token"
    class MockExternalLibTokenException(Exception):
        def __init__(self, message, code=None):
            super().__init__(message)
            self.message = message
            self.code = code
    MockExternalLibTokenException.__name__ = "TokenException"
    client.mock_kc_instance.generate_session.side_effect = MockExternalLibTokenException(error_message, code=403)
    with pytest.raises(TokenException) as excinfo:
        client.generate_session(MOCK_REQUEST_TOKEN)
    assert error_message in str(excinfo.value)
    assert excinfo.value.code == 403

def test_generate_session_kiteconnect_raises_general_exception(client_setup):
    client = client_setup
    error_message = "Some other API error without message/code attributes"
    kc_generic_exception = TypeError(error_message)
    client.mock_kc_instance.generate_session.side_effect = kc_generic_exception
    with pytest.raises(GeneralException) as excinfo:
        client.generate_session(MOCK_REQUEST_TOKEN)
    assert f"An underlying error occurred during session generation: {kc_generic_exception}" in str(excinfo.value)

@patch('kite_wrapper.client.KiteConfig')
@patch('kite_wrapper.client.KiteConnect')
def test_generate_session_no_kiteconnect_client(MockKiteConnect_class_direct, MockKiteConfig_class_direct, mock_kite_config):
    MockKiteConfig_class_direct.return_value = mock_kite_config
    MockKiteConnect_class_direct.side_effect = Exception("KC init failed")
    client = KiteClient(api_key=MOCK_API_KEY, api_secret=MOCK_API_SECRET)
    assert client.kite_connect_client is None
    with pytest.raises(GeneralException) as excinfo:
        client.generate_session(MOCK_REQUEST_TOKEN)
    assert "KiteConnect client not initialized" in str(excinfo.value)

# Tests for _request method (Need to use a client where _request is NOT mocked, or adjust fixture)
# For these tests, we will create a new client instance or adjust client_setup not to mock _request globally.
# Let's create a slightly different fixture for _request tests.
@pytest.fixture
@patch('kite_wrapper.client.KiteConfig')
@patch('kite_wrapper.client.KiteConnect')
def client_for_request_tests(MockKiteConnect_class, MockKiteConfig_class, mock_kite_config):
    MockKiteConfig_class.return_value = mock_kite_config
    mock_kc_instance = MagicMock()
    MockKiteConnect_class.return_value = mock_kc_instance
    # DO NOT mock client._request here
    client = KiteClient(api_key=MOCK_API_KEY, api_secret=MOCK_API_SECRET, access_token=MOCK_ACCESS_TOKEN)
    return client


@patch('requests.Session.request') # Mock at the source of the actual HTTP call
def test_request_get_success(mock_actual_session_request, client_for_request_tests):
    client = client_for_request_tests
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"status": "success", "data": "some data"}
    mock_actual_session_request.return_value = mock_response

    response = client._request("GET", "/test/route", params={"key": "value"})

    assert response == {"status": "success", "data": "some data"}
    mock_actual_session_request.assert_called_once_with(
        "GET", "https://api.kite.trade/test/route", params={"key": "value"}, data=None, json=None,
        timeout=client._timeout, proxies=client.proxies, verify=True )

@patch('requests.Session.request')
def test_request_post_success_json(mock_actual_session_request, client_for_request_tests):
    client = client_for_request_tests
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"status": "success", "data": "posted data"}
    mock_actual_session_request.return_value = mock_response
    post_data = {"order_id": 123, "type": "MARKET"}
    response = client._request("POST", "/test/order", data=post_data, is_json=True)
    assert response == {"status": "success", "data": "posted data"}
    mock_actual_session_request.assert_called_once_with(
        "POST", "https://api.kite.trade/test/order", params=None, data=None, json=post_data,
        timeout=client._timeout, proxies=client.proxies, verify=True )

@patch('requests.Session.request')
def test_request_post_success_form(mock_actual_session_request, client_for_request_tests):
    client = client_for_request_tests
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"status": "success", "message": "form processed"}
    mock_actual_session_request.return_value = mock_response
    form_data = {"item_id": "xyz", "quantity": "10"}
    response = client._request("POST", "/test/form", data=form_data, is_json=False)
    assert response == {"status": "success", "message": "form processed"}
    mock_actual_session_request.assert_called_once_with(
        "POST", "https://api.kite.trade/test/form", params=None, data=form_data, json=None,
        timeout=client._timeout, proxies=client.proxies, verify=True )

@patch('requests.Session.request')
def test_request_network_error(mock_actual_session_request, client_for_request_tests):
    client = client_for_request_tests
    mock_actual_session_request.side_effect = requests.exceptions.Timeout("Connection timed out")
    with pytest.raises(NetworkException) as excinfo:
        client._request("GET", "/test/timeout")
    assert "Network error: Connection timed out" in str(excinfo.value)

@patch('requests.Session.request')
def test_request_json_parse_error(mock_actual_session_request, client_for_request_tests):
    client = client_for_request_tests
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.side_effect = ValueError("Malformed JSON")
    mock_response.content = b"This is not valid JSON"
    mock_actual_session_request.return_value = mock_response
    with pytest.raises(DataException) as excinfo:
        client._request("GET", "/test/malformed")
    assert "Failed to parse JSON response: b'This is not valid JSON'" in str(excinfo.value)

@patch('requests.Session.request')
def test_request_non_json_response_text(mock_actual_session_request, client_for_request_tests):
    client = client_for_request_tests
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/csv"}
    mock_response.text = "col1,col2\nval1,val2"
    mock_actual_session_request.return_value = mock_response
    response = client._request("GET", "/test/csvdata")
    assert response == "col1,col2\nval1,val2"

@pytest.mark.parametrize("status_code, error_type, error_message, expected_exception", [
    (400, "InputException", "Invalid input parameters", InputException),
    (403, "TokenException", "Access token is invalid or expired", TokenException),
    (403, "PermissionException", "User does not have permission", PermissionException),
    (429, "NetworkException", "Too many requests", NetworkException),
    (500, "GeneralException", "Internal server error", GeneralException),
    (503, "NetworkException", "Service unavailable", NetworkException),
    (404, None, "Resource not found (HTML page)", KiteException),
    (401, "TokenException", "Unauthorized access", TokenException)
])
@patch('requests.Session.request')
def test_request_http_errors_mapped(mock_actual_session_request, client_for_request_tests, status_code, error_type, error_message, expected_exception):
    client = client_for_request_tests
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if error_type:
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"error_type": error_type, "message": error_message}
    else:
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = error_message
    mock_actual_session_request.return_value = mock_response
    with pytest.raises(expected_exception) as excinfo:
        client._request("GET", f"/test/error/{status_code}")
    assert error_message in str(excinfo.value)
    if hasattr(excinfo.value, 'code'):
        assert excinfo.value.code == status_code

# Tests for actual API endpoint methods
def test_profile(client_setup): # Uses client_setup where _request is mocked
    client = client_setup
    expected_profile_data = {"user_id": "AB1234", "user_name": "Test User"}
    client._request.return_value = expected_profile_data # Mock the return value of _request

    profile_data = client.profile()

    assert profile_data == expected_profile_data
    client._request.assert_called_once_with("GET", "/user/profile")

def test_margins(client_setup):
    client = client_setup
    expected_margins_data = {"equity": {"net": 1000.0}, "commodity": {"net": 2000.0}}
    client._request.return_value = expected_margins_data

    # Test margins without segment
    margins_data_all = client.margins()
    assert margins_data_all == expected_margins_data
    client._request.assert_called_with("GET", "/user/margins") # Use assert_called_with for multiple calls on _request

    # Test margins with segment
    client._request.reset_mock() # Reset mock for the next call
    client._request.return_value = {"equity": {"net": 1000.0}} # Simulate response for specific segment
    margins_data_equity = client.margins(segment="equity")
    assert margins_data_equity == {"equity": {"net": 1000.0}}
    client._request.assert_called_once_with("GET", "/user/margins/equity")

# Example of how one might test an endpoint that takes parameters
def test_place_order(client_setup): # Assuming a place_order method exists
    client = client_setup
    order_params = {
        "tradingsymbol": "INFY", "exchange": "NSE", "transaction_type": "BUY",
        "order_type": "MARKET", "quantity": 1
    }
    expected_response = {"status": "success", "order_id": "123456789"}
    client._request.return_value = expected_response

    # Hypothetical method: client.place_order(**order_params)
    # For now, let's simulate a direct call to _request for a POST to show how it would work
    # response = client.place_order("variety", **order_params)
    # client._request.assert_called_once_with("POST", "/orders/variety", data=order_params, is_json=True)

    # Let's assume client.margins() was a POST for demonstration (it's a GET, but for structure)
    # To test a method that uses POST and parameters:
    # client.some_post_method(param1="value1", data_payload={"key": "value"})
    # client._request.assert_called_once_with("POST", "/some/route/param1=value1", data={"key":"value"}, is_json=True)
    pass # Placeholder as place_order is not yet implemented in client.py

# TODO: Add more Kite API method wrappers here (orders, positions, holdings, historical_data, etc.)
# And add corresponding tests for them, similar to test_profile and test_margins.

# Tests for newly added API endpoint methods

def test_place_order(client_setup):
    client = client_setup
    order_params = {
        "variety": "regular", "exchange": "NSE", "tradingsymbol": "INFY",
        "transaction_type": "BUY", "quantity": 1, "product": "CNC",
        "order_type": "MARKET", "price": None, "validity": "DAY",
        "disclosed_quantity": 0, "trigger_price": 0, "squareoff": 0,
        "stoploss": 0, "trailing_stoploss": 0, "tag": "mytest"
    }
    # Filter out None values as the method implementation does
    expected_payload = {k: v for k, v in order_params.items() if k != "variety" and v is not None}

    client._request.return_value = {"status": "success", "data": {"order_id": "12345"}}

    response = client.place_order(
        variety=order_params["variety"], exchange=order_params["exchange"],
        tradingsymbol=order_params["tradingsymbol"], transaction_type=order_params["transaction_type"],
        quantity=order_params["quantity"], product=order_params["product"],
        order_type=order_params["order_type"], price=order_params["price"],
        validity=order_params["validity"], disclosed_quantity=order_params["disclosed_quantity"],
        trigger_price=order_params["trigger_price"], squareoff=order_params["squareoff"],
        stoploss=order_params["stoploss"], trailing_stoploss=order_params["trailing_stoploss"],
        tag=order_params["tag"]
    )

    assert response == {"status": "success", "data": {"order_id": "12345"}}
    client._request.assert_called_once_with("POST", f"/orders/{order_params['variety']}", data=expected_payload, is_json=True)

def test_modify_order(client_setup):
    client = client_setup
    modify_params = {
        "variety": "regular", "order_id": "12345", "quantity": 2, "price": 150.5,
        "order_type": "LIMIT", "trigger_price": 0 # Example, adjust as needed
    }
    expected_payload = {
        "quantity": 2, "price": 150.5, "order_type": "LIMIT", "trigger_price": 0
    }
    client._request.return_value = {"status": "success", "data": {"order_id": "12345"}}

    response = client.modify_order(
        variety=modify_params["variety"], order_id=modify_params["order_id"],
        quantity=modify_params["quantity"], price=modify_params["price"],
        order_type=modify_params["order_type"], trigger_price=modify_params["trigger_price"]
    )
    assert response == {"status": "success", "data": {"order_id": "12345"}}
    client._request.assert_called_once_with("PUT", f"/orders/{modify_params['variety']}/{modify_params['order_id']}", data=expected_payload, is_json=True)

def test_cancel_order(client_setup):
    client = client_setup
    variety = "regular"
    order_id = "12345"
    parent_order_id = "parent123"
    client._request.return_value = {"status": "success", "data": {"order_id": "12345"}}

    # Test with parent_order_id
    response = client.cancel_order(variety=variety, order_id=order_id, parent_order_id=parent_order_id)
    assert response == {"status": "success", "data": {"order_id": "12345"}}
    client._request.assert_called_once_with("DELETE", f"/orders/{variety}/{order_id}", params={"parent_order_id": parent_order_id})

    client._request.reset_mock()
    # Test without parent_order_id
    response = client.cancel_order(variety=variety, order_id=order_id)
    assert response == {"status": "success", "data": {"order_id": "12345"}}
    client._request.assert_called_once_with("DELETE", f"/orders/{variety}/{order_id}", params=None)


def test_get_order_history(client_setup):
    client = client_setup
    order_id = "12345"
    expected_response = [{"status": "COMPLETE"}, {"status": "PENDING"}]
    client._request.return_value = expected_response

    response = client.get_order_history(order_id)
    assert response == expected_response
    client._request.assert_called_once_with("GET", f"/orders/{order_id}")

def test_get_trades_for_order(client_setup):
    client = client_setup
    order_id = "12345"
    expected_response = [{"trade_id": "t1"}, {"trade_id": "t2"}]
    client._request.return_value = expected_response

    response = client.get_trades(order_id=order_id)
    assert response == expected_response
    client._request.assert_called_once_with("GET", f"/orders/{order_id}/trades")

def test_get_all_trades(client_setup):
    client = client_setup
    expected_response = [{"trade_id": "t3"}, {"trade_id": "t4"}]
    client._request.return_value = expected_response

    response = client.get_trades() # No order_id
    assert response == expected_response
    client._request.assert_called_once_with("GET", "/trades")

def test_get_positions(client_setup):
    client = client_setup
    expected_response = {"net": [], "day": []}
    client._request.return_value = expected_response

    response = client.get_positions()
    assert response == expected_response
    client._request.assert_called_once_with("GET", "/portfolio/positions")

def test_get_holdings(client_setup):
    client = client_setup
    expected_response = [{"tradingsymbol": "INFY", "quantity": 10}]
    client._request.return_value = expected_response

    response = client.get_holdings()
    assert response == expected_response
    client._request.assert_called_once_with("GET", "/portfolio/holdings")

def test_get_instruments_all(client_setup):
    client = client_setup
    expected_csv_data = "instrument_token,exchange_token,tradingsymbol\n123,456,INFY"
    client._request.return_value = expected_csv_data # _request returns text for non-JSON

    response = client.get_instruments()
    assert response == expected_csv_data
    client._request.assert_called_once_with("GET", "/instruments")

def test_get_instruments_for_exchange(client_setup):
    client = client_setup
    exchange = "NSE"
    expected_csv_data = "instrument_token,exchange_token,tradingsymbol\n789,012,RELIANCE"
    client._request.return_value = expected_csv_data

    response = client.get_instruments(exchange=exchange)
    assert response == expected_csv_data
    client._request.assert_called_once_with("GET", f"/instruments/{exchange.upper()}")

def test_get_quote(client_setup):
    client = client_setup
    instruments = ["NSE:INFY", "BSE:RELIANCE"]
    expected_response = {
        "NSE:INFY": {"last_price": 1500.0},
        "BSE:RELIANCE": {"last_price": 2200.0}
    }
    client._request.return_value = expected_response

    response = client.get_quote(*instruments) # Pass as *args
    assert response == expected_response
    client._request.assert_called_once_with("GET", "/quote", params={"i": list(instruments)})

def test_get_quote_no_instruments(client_setup):
    client = client_setup
    with pytest.raises(InputException) as excinfo:
        client.get_quote()
    assert "At least one instrument must be provided" in str(excinfo.value)
    client._request.assert_not_called()

def test_get_historical_data(client_setup):
    client = client_setup
    params = {
        "instrument_token": "12345",
        "from_date": "2023-01-01",
        "to_date": "2023-01-02",
        "interval": "minute",
        "continuous": False,
        "oi": False
    }
    expected_response = [["2023-01-01 09:15:00", 100, 102, 99, 101, 1000]]
    client._request.return_value = expected_response

    response = client.get_historical_data(**params)
    assert response == expected_response

    expected_api_params = {
        "from": params["from_date"],
        "to": params["to_date"],
        "continuous": 0, # False becomes 0
        "oi": 0          # False becomes 0
    }
    client._request.assert_called_once_with(
        "GET",
        f"/instruments/historical/{params['instrument_token']}/{params['interval']}",
        params=expected_api_params
    )

def test_get_historical_data_continuous_oi_true(client_setup):
    client = client_setup
    params = {
        "instrument_token": "54321",
        "from_date": "2023-02-01",
        "to_date": "2023-02-02",
        "interval": "day",
        "continuous": True,
        "oi": True
    }
    client._request.return_value = [["2023-02-01", 200, 202, 199, 201, 2000, 5000]]

    client.get_historical_data(**params)

    expected_api_params = {
        "from": params["from_date"],
        "to": params["to_date"],
        "continuous": 1, # True becomes 1
        "oi": 1          # True becomes 1
    }
    client._request.assert_called_once_with(
        "GET",
        f"/instruments/historical/{params['instrument_token']}/{params['interval']}",
        params=expected_api_params
    )

# Placeholder for a test that checks for error handling from _request
def test_method_error_handling(client_setup):
    client = client_setup
    client._request.side_effect = TokenException("Token expired", code=403)

    with pytest.raises(TokenException) as excinfo:
        client.get_positions() # Any method that uses _request

    assert "Token expired" in str(excinfo.value)
    assert excinfo.value.code == 403
