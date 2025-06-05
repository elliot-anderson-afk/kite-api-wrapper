import requests
import logging
from urllib.parse import urljoin

from kiteconnect import KiteConnect # Assuming this is the actual library

from kite_wrapper.config import KiteConfig
from kite_wrapper.exceptions import (KiteException, TokenException, GeneralException,
                                     PermissionException, OrderException, InputException,
                                     DataException, NetworkException)

log = logging.getLogger(__name__)


class KiteClient:
    _API_VERSION = "3"
    _root = "https://api.kite.trade"
    _timeout = 7

    _exception_map = {
        "TokenException": TokenException,
        "GeneralException": GeneralException,
        "PermissionException": PermissionException,
        "OrderException": OrderException,
        "InputException": InputException,
        "DataException": DataException,
        "NetworkException": NetworkException,
        # Add other specific KiteConnect exceptions if they exist and need mapping
    }

    def __init__(self, api_key=None, api_secret=None, access_token=None, config_path=None,
                 debug=False, timeout=None, proxies=None, pool=None):
        self.config = KiteConfig(api_key=api_key, api_secret=api_secret,
                                 access_token=access_token, config_path=config_path)
        self.debug = debug
        self.access_token = self.config.get_access_token()
        self.api_key = self.config.get_api_key()
        self.api_secret = self.config.get_api_secret()
        self._timeout = timeout if timeout else self._timeout
        self.proxies = proxies if proxies else {}

        try:
            self.kite_connect_client = KiteConnect(
                api_key=self.api_key,
                access_token=self.access_token,
                proxies=self.proxies,
                root=self._root
            )
            if self.access_token:
                 self.kite_connect_client.set_access_token(self.access_token)
        except Exception as e:
            log.error(f"Failed to initialize underlying KiteConnect client: {e}")
            self.kite_connect_client = None

        self.session = requests.Session()
        if pool:
            pass

        self._update_headers()

        if self.debug:
            logging.basicConfig(level=logging.DEBUG)

    def _update_headers(self):
        headers = {
            "X-Kite-Version": self._API_VERSION,
            "User-Agent": "KiteConnect-Python/3"
        }
        if self.api_key:
            headers["Authorization"] = f"token {self.api_key}:{self.access_token if self.access_token else ''}"
        self.session.headers.update(headers)

    def _request(self, method, route, params=None, data=None, is_json=False):
        if params is None:
            params = {}
        params = {k: v for k, v in params.items() if v is not None}
        uri = urljoin(self._root, route)
        log.debug(f"Request: {method} {uri} with params {params} and data {data}")
        self._update_headers()

        try:
            response = self.session.request(
                method,
                uri,
                params=params if method == "GET" else None,
                data=data if method != "GET" and not is_json else None,
                json=data if is_json else None,
                timeout=self._timeout,
                proxies=self.proxies,
                verify=True
            )
        except requests.exceptions.RequestException as e:
            raise NetworkException(f"Network error: {e}")

        log.debug(f"Response: {response.status_code} {response.content}")

        if "application/json" in response.headers.get("content-type", ""):
            try:
                data = response.json()
            except ValueError:
                raise DataException(f"Failed to parse JSON response: {response.content}")
        else:
            data = response.text

        if response.status_code >= 400:
            if isinstance(data, dict) and data.get("error_type"):
                error_type = data["error_type"]
                exception_class = self._exception_map.get(error_type, KiteException)
                raise exception_class(data.get("message", "Unknown error"), code=response.status_code)
            else:
                raise KiteException(f"HTTP error: {response.status_code} - {response.text}", code=response.status_code)
        return data

    def set_access_token(self, access_token):
        self.access_token = access_token
        self.config.set_access_token(access_token)
        self._update_headers()
        if self.kite_connect_client:
            self.kite_connect_client.set_access_token(access_token)
        log.debug("Access token updated.")

    def login_url(self):
        if self.kite_connect_client:
            return self.kite_connect_client.login_url()
        else:
            return f"{self._root}/connect/login?api_key={self.api_key}&v={self._API_VERSION}"

    def generate_session(self, request_token, api_secret=None):
        if not self.kite_connect_client:
            raise GeneralException("KiteConnect client not initialized. Cannot generate session.")

        try:
            secret_to_use = api_secret if api_secret else self.api_secret
            if not secret_to_use:
                raise InputException("API secret is required to generate a session.")

            session_data = self.kite_connect_client.generate_session(request_token, api_secret=secret_to_use)

            if "access_token" in session_data:
                self.set_access_token(session_data["access_token"])
                log.info("Session generated successfully. Access token set.")
                return session_data
            else:
                raise TokenException("Failed to generate session: 'access_token' not found in response.",
                                     code=session_data.get("status_code"))
        except KiteException:
            raise
        except Exception as e:
            log.error(f"Error generating session via KiteConnect: {e} (Type: {type(e).__name__})")
            if hasattr(e, "message") and hasattr(e, "code"):
                error_type_name = type(e).__name__
                exception_class = self._exception_map.get(error_type_name, KiteException)
                if error_type_name in self._exception_map:
                    raise exception_class(e.message, code=e.code)
                else:
                    raise GeneralException(f"Underlying library error ({error_type_name}): {e.message}", code=e.code)
            raise GeneralException(f"An underlying error occurred during session generation: {e}")

    def margins(self, segment=None):
        route = "/user/margins"
        if segment:
            route = f"/user/margins/{segment}"
        return self._request("GET", route)

    def profile(self):
        return self._request("GET", "/user/profile")

    # методы API будут вставлены сюда
    # Correctly indented new methods:
    def place_order(self, variety, exchange, tradingsymbol, transaction_type, quantity,
                    product, order_type, price=None, validity=None,
                    disclosed_quantity=None, trigger_price=None,
                    squareoff=None, stoploss=None, trailing_stoploss=None,
                    tag=None):
        """Place an order.
        Refer to the Kite Connect API documentation for detailed parameter descriptions.
        Example: place_order("regular", "NSE", "INFY", "BUY", 1, "CNC", "MARKET")
        """
        params = locals()
        del params["self"]
        del params["variety"]
        payload = {k: v for k, v in params.items() if v is not None}
        route = f"/orders/{variety}"
        return self._request("POST", route, data=payload, is_json=True)

    def modify_order(self, variety, order_id, parent_order_id=None,
                     quantity=None, price=None, order_type=None,
                     trigger_price=None, validity=None, disclosed_quantity=None):
        """Modify an open order.
        Refer to the Kite Connect API documentation for detailed parameter descriptions.
        """
        params = locals()
        del params["self"]
        del params["variety"]
        del params["order_id"] # order_id is part of the route
        payload = {k: v for k, v in params.items() if v is not None}
        route = f"/orders/{variety}/{order_id}"
        return self._request("PUT", route, data=payload, is_json=True)

    def cancel_order(self, variety, order_id, parent_order_id=None):
        """Cancel an open order.
        Refer to the Kite Connect API documentation for detailed parameter descriptions.
        """
        payload = {}
        if parent_order_id: # parent_order_id is optional
            payload["parent_order_id"] = parent_order_id
        route = f"/orders/{variety}/{order_id}"
        return self._request("DELETE", route, params=payload if payload else None)

    def get_order_history(self, order_id):
        """Retrieve the history of a specific order.
        :param order_id: ID of the order.
        :returns: A list of order updates.
        """
        route = f"/orders/{order_id}"
        return self._request("GET", route)

    def get_trades(self, order_id=None):
        """Retrieve trades for a specific order or all trades for the day if order_id is None.
        :param order_id: ID of the order (optional).
        :returns: List of trade details.
        """
        if order_id:
            route = f"/orders/{order_id}/trades"
        else:
            route = "/trades"
        return self._request("GET", route)

    def get_positions(self):
        """Retrieve the current open net positions for all segments.
        :returns: Dict with 'net' and 'day' positions.
        """
        route = "/portfolio/positions"
        return self._request("GET", route)

    def get_holdings(self):
        """Retrieve current equity and mutual fund holdings.
        :returns: List of holding details.
        """
        route = "/portfolio/holdings"
        return self._request("GET", route)

    def get_instruments(self, exchange=None):
        """
        Retrieve the dump of all tradable instruments.
        :param exchange: Optional. Name of the exchange (e.g., "NSE", "BSE", "NFO", "MCX").
                         If None, retrieves for all enabled exchanges.
        :returns: CSV string of instruments.
        """
        route = "/instruments"
        if exchange:
            route = f"/instruments/{exchange.upper()}"
        return self._request("GET", route)

    def get_quote(self, *instruments):
        """
        Retrieve live market quotes for one or more instruments.
        :param instruments: One or more instrument identifiers in the format 'EXCHANGE:TRADINGSYMBOL'
                            (e.g., "NSE:INFY", "MCX:SILVERMIC20DECFUT").
        :returns: Dict with quote data for the requested instruments.
        Example: get_quote("NSE:INFY", "NSE:RELIANCE")
        """
        if not instruments:
            raise InputException("At least one instrument must be provided for a quote.")
        params = {"i": list(instruments)}
        route = "/quote"
        return self._request("GET", route, params=params)

    def get_historical_data(self, instrument_token, from_date, to_date, interval, continuous=False, oi=False):
        """
        Retrieve historical OHLC and volume data for an instrument.
        :param instrument_token: Numerical identifier for the instrument (from instrument dump).
        :param from_date: From date (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD).
        :param to_date: To date (YYYY-MM-DD HH:MM:SS or YYYY-MM-DD).
        :param interval: Candle interval ('minute', 'day', '3minute', '5minute', '10minute',
                                        '15minute', '30minute', '60minute').
        :param continuous: Boolean for continuous future contract data (default False).
        :param oi: Boolean to fetch OI data along with OHLCV (default False).
        :returns: List of candle data.
        """
        continuous_int = 1 if continuous else 0
        oi_int = 1 if oi else 0
        final_params = {
            "from": from_date,
            "to": to_date,
            "continuous": continuous_int,
            "oi": oi_int
        }
        route = f"/instruments/historical/{instrument_token}/{interval}"
        return self._request("GET", route, params=final_params)

    def __repr__(self):
        return f"<KiteClient api_key='{self.api_key[:4] if self.api_key else 'None'}...'>"


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    log.info("KiteClient example script started.")
    try:
        client = KiteClient(debug=True)
        log.info(f"Client initialized: {client}")
        log.info(f"API Key: {client.api_key[:5] if client.api_key else 'N/A'}...")
        login_url = client.login_url()
        log.info(f"Login URL: {login_url}")
        print(f"Please login using this URL: {login_url}")
        request_token_input = input("Enter the request_token obtained after login: ")
        if request_token_input:
            try:
                session = client.generate_session(request_token_input.strip())
                log.info(f"Session generated: {session}")
                log.info(f"Access Token: {client.access_token[:5] if client.access_token else 'N/A'}...")
                profile_data = client.profile()
                log.info(f"Profile: {profile_data}")
                margins_data = client.margins()
                log.info(f"Margins: {margins_data}")
            except KiteException as e:
                log.error(f"Kite API Error: {e} (Code: {e.code})")
            except Exception as e:
                log.error(f"An unexpected error occurred: {e}", exc_info=True)
        else:
            log.warning("No request_token entered. Skipping session generation and authenticated calls.")
    except DataException as e:
        log.error(f"Configuration Error: {e}")
    except Exception as e:
        log.error(f"An unexpected error occurred during setup: {e}", exc_info=True)
