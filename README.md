# Python Kite API Wrapper

A Python wrapper for the Kite Connect API, designed to simplify interactions for placing orders, managing positions, retrieving market data, and more. This wrapper handles API credentials securely via a configuration file or environment variables.

## Features

*   Manages API key, API secret, and access token.
*   Credentials can be loaded from:
    *   Direct parameters during client initialization.
    *   Environment variables.
    *   A `.ini` configuration file (default: `~/.kite/config.ini`).
*   Handles Kite Connect API authentication flow.
*   Provides wrapper methods for common API endpoints:
    *   User Profile & Margins
    *   Order Management (Place, Modify, Cancel, History, Trades)
    *   Portfolio (Holdings, Positions)
    *   Market Data (Instruments, Quotes, Historical Data)
*   Custom exceptions for better error handling.
*   Session persistence for access tokens (saved to config file).

## Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    # python -m venv venv  # Removed this line for tool compatibility
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
    The main dependencies are `requests` and `kiteconnect`.

## Configuration

Credentials (API Key, API Secret, Access Token) are loaded with the following precedence:

1.  **Directly passed parameters** to `KiteClient` or `KiteConfig`.
2.  **Environment Variables**:
    *   `KITE_API_KEY`
    *   `KITE_API_SECRET`
    *   `KITE_ACCESS_TOKEN` (optional, can be generated)
3.  **Configuration File**:
    *   By default, the wrapper looks for `config.ini` at `~/.kite/config.ini`.
    *   You can specify a custom path when initializing `KiteClient(config_path="path/to/your/config.ini")`.
    *   Create a config file based on `config.ini.example`:
        ```ini
        [Kite]
        api_key = YOUR_API_KEY
        api_secret = YOUR_API_SECRET
        # access_token can be omitted here and generated/saved by the client
        ```

## Usage

### 1. Initialization

```python
from kite_wrapper import KiteClient, KiteConfig
from kite_wrapper.exceptions import KiteException, DataException

# Option 1: Using environment variables or default config file (~/.kite/config.ini)
try:
    client = KiteClient(debug=True) # debug=True for verbose logging
except DataException as e:
    print(f"Configuration error: {e}")
    # Handle missing API key/secret
    # exit() # Replaced exit() with a comment for tool compatibility
except Exception as e:
    print(f"Error initializing client: {e}")
    # exit() # Replaced exit() with a comment for tool compatibility


# Option 2: Specifying config file path
# client = KiteClient(config_path="path/to/your/custom_config.ini")

# Option 3: Passing credentials directly (least recommended for secrets)
# client = KiteClient(api_key="YOUR_KEY", api_secret="YOUR_SECRET")
```

### 2. Authentication (Generating Access Token)

The `access_token` is required for most API calls. If it's not available in your config or environment, you need to generate it using the Kite Connect login flow.

```python
if not client.access_token:
    print("Access token not found. Starting login flow...")
    login_url = client.login_url()
    print(f"Please login using this URL: {login_url}")

    try:
        request_token = input("Enter the request_token obtained after successful login: ")
        session_data = client.generate_session(request_token.strip())

        print(f"Session generated successfully! Access Token: {client.access_token[:10]}...")
        # The new access_token is automatically saved to your config file if one was used.
    except KiteException as e:
        print(f"Authentication Error: {e.message} (Code: {e.code})")
    except Exception as e:
        print(f"An unexpected error occurred during authentication: {e}")
else:
    print(f"Using existing access token: {client.access_token[:10]}...")
```

### 3. Making API Calls

Once the client is initialized and `access_token` is set:

```python
try:
    # Get user profile
    profile = client.profile()
    print(f"Profile: {profile.get('user_name')}")

    # Get margins
    margins = client.margins()
    # print(f"Margins: {margins}") # Full margin data can be verbose

    # Get holdings
    holdings = client.get_holdings()
    print(f"Number of holdings: {len(holdings)}")

    # Get positions
    positions = client.get_positions()
    # print(f"Positions: {positions}")

    # Get quotes
    quotes = client.get_quote("NSE:INFY", "MCX:CRUDEOIL23DECFUT")
    # print(f"Quote for INFY: {quotes.get('NSE:INFY', {}).get('last_price')}")

    # Get historical data
    # Ensure you have the correct instrument_token (integer ID) from get_instruments()
    # For example, historical_data = client.get_historical_data(instrument_token="123456",
    #                                                       from_date="2023-01-01",
    #                                                       to_date="2023-01-10",
    #                                                       interval="day")
    # print(f"Historical data (first candle): {historical_data[0] if historical_data else 'No data'}")

    # Place an order (Example - use with caution!)
    # order_response = client.place_order(
    #     variety="regular",
    #     exchange="NSE",
    #     tradingsymbol="INFY-EQ", # Ensure correct symbol format
    #     transaction_type="BUY",
    #     quantity=1,
    #     product="CNC",
    #     order_type="MARKET"
    # )
    # print(f"Order placement response: {order_response}")

except KiteException as e:
    print(f"API Error: {e.message} (Code: {e.code})")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

```

## Available Client Methods

Here's a list of the primary methods available on the `KiteClient` instance:

*   **Authentication & Configuration:**
    *   `KiteClient(api_key=None, api_secret=None, access_token=None, config_path=None, debug=False, ...)`: Constructor.
    *   `set_access_token(access_token)`: Manually set/update the access token.
    *   `login_url()`: Get the URL for manual login to obtain a `request_token`.
    *   `generate_session(request_token, api_secret=None)`: Exchange `request_token` for `access_token` and other session details.

*   **User Info:**
    *   `profile()`: Get user profile details.
    *   `margins(segment=None)`: Get account margins (equity/commodity).

*   **Order Management:**
    *   `place_order(variety, exchange, tradingsymbol, transaction_type, quantity, product, order_type, price=None, ...)`: Place a new order.
    *   `modify_order(variety, order_id, quantity=None, price=None, ...)`: Modify an existing order.
    *   `cancel_order(variety, order_id, parent_order_id=None)`: Cancel an order.
    *   `get_order_history(order_id)`: Get history for a specific order.
    *   `get_trades(order_id=None)`: Get trades for an order or all trades for the day.

*   **Portfolio:**
    *   `get_positions()`: Get current open positions.
    *   `get_holdings()`: Get list of holdings.

*   **Market Data:**
    *   `get_instruments(exchange=None)`: Get a dump of tradable instruments (CSV format).
    *   `get_quote(*instruments)`: Get live quotes for specified instruments.
    *   `get_historical_data(instrument_token, from_date, to_date, interval, continuous=False, oi=False)`: Get historical OHLC data.

*Note: Refer to the docstrings in `kite_wrapper/client.py` for detailed parameter information for each method.*

## Exception Handling

The wrapper uses custom exceptions (defined in `kite_wrapper/exceptions.py`) that inherit from `KiteException`. This allows for more granular error handling:

*   `KiteException`: Base exception.
*   `GeneralException`: Unclassified error.
*   `TokenException`: Authentication or token issue.
*   `PermissionException`: User permission error.
*   `OrderException`: Order placement/modification error.
*   `InputException`: Invalid input parameters.
*   `DataException`: Data parsing or configuration error.
*   `NetworkException`: Network issue or timeout.

Always wrap API calls in `try...except KiteException as e:` blocks.

## Development

(Optional: Add notes on running tests, linters, etc. if this were a larger project meant for collaboration)

```bash
# Run tests (requires pytest)
pytest
```

## Disclaimer

This is an unofficial wrapper. Trading financial instruments involves substantial risk of loss. Use this software at your own risk. Ensure you understand the Kite Connect API terms of service.
