import logging
from kite_wrapper import KiteClient
from kite_wrapper.exceptions import KiteException, DataException, TokenException

# Configure basic logging for the example
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def run_example():
    log.info("Starting Kite API Wrapper example...")

    try:
        # Initialize KiteClient.
        # Assumes API key/secret are set via environment variables (KITE_API_KEY, KITE_API_SECRET)
        # or in the default config file (~/.kite/config.ini).
        # For this example, set debug=True for more verbose output from the client.
        client = KiteClient(debug=True)
        log.info("KiteClient initialized.")

    except DataException as e:
        log.error(f"Configuration Error: {e}. Please ensure API key and secret are set.")
        log.error("You can set them as environment variables (KITE_API_KEY, KITE_API_SECRET) or in a config file.")
        return
    except Exception as e:
        log.error(f"Error initializing client: {e}")
        return

    # --- Authentication ---
    if not client.access_token:
        log.info("Access token not found. Initiating login flow.")
        login_url = client.login_url()
        print(f"Please open this URL in your browser to login: {login_url}")

        try:
            request_token = input("After successful login, please enter the request_token from the redirect URL: ").strip()
            if not request_token:
                log.error("Request token not provided. Exiting.")
                return

            log.info(f"Attempting to generate session with request_token: {request_token[:10]}...")
            session_data = client.generate_session(request_token)
            log.info(f"Session generated successfully! User ID: {session_data.get('user_id')}")
            log.info(f"Access Token (first 10 chars): {client.access_token[:10]}...")
            # The new access token is automatically saved if a config file path was used and is writable.
            print("\nAccess token has been obtained and is ready for use (and saved if config file is used).\n")

        except TokenException as e:
            log.error(f"Authentication Error (TokenException): {e.message} (Code: {e.code})")
            return
        except KiteException as e:
            log.error(f"API Error during authentication: {e.message} (Code: {e.code})")
            return
        except Exception as e:
            log.error(f"An unexpected error occurred during authentication: {e}")
            return
    else:
        log.info(f"Existing access token found (first 10 chars): {client.access_token[:10]}...")

    # --- Making API Calls ---
    try:
        log.info("\n--- Fetching User Profile ---")
        profile = client.profile()
        if profile and isinstance(profile, dict): # Check if profile is not None and is a dict
            log.info(f"User Profile: Name - {profile.get('user_name')}, Email - {profile.get('email')}")
        else:
            log.warning(f"Could not retrieve valid profile data. Response: {profile}")


        log.info("\n--- Fetching Holdings ---")
        holdings = client.get_holdings()
        if holdings is not None: # Holdings can be an empty list
            log.info(f"Number of holdings: {len(holdings)}")
            if holdings:
                log.info(f"First holding example: {holdings[0].get('tradingsymbol')}, Qty: {holdings[0].get('quantity')}")
        else:
            log.warning("Could not retrieve holdings or response was None.")


        log.info("\n--- Fetching Positions ---")
        positions = client.get_positions()
        if positions and isinstance(positions, dict): # Positions has 'net' and 'day' keys
             log.info(f"Net positions count: {len(positions.get('net', []))}")
             log.info(f"Day positions count: {len(positions.get('day', []))}")
        else:
            log.warning(f"Could not retrieve valid positions data. Response: {positions}")


        log.info("\n--- Example: Getting Quotes ---")
        # Replace with actual tradable symbols if you run this.
        # Ensure the symbols are correct for your account and market segment.
        # For example, "NSE:INFY-EQ" or "NSE:SBIN-EQ" for equity.
        # The default `kiteconnect` library and this wrapper expect symbols like "NSE:INFY" or "NFO:NIFTY23DECFUT"
        instruments_to_quote = ["NSE:INFY", "NSE:RELIANCE"]
        quotes = client.get_quote(*instruments_to_quote)
        if quotes:
            for instrument, data in quotes.items():
                log.info(f"Quote for {instrument}: LTP = {data.get('last_price')}, Open = {data.get('ohlc',{}).get('open')}, Close = {data.get('ohlc',{}).get('close')}")
        else:
            log.warning("Could not retrieve quotes or response was empty/invalid.")

        # --- Example: Placing an Order (DEMO - DO NOT RUN UNMODIFIED IN PRODUCTION) ---
        # log.info("\n--- Example: Placing a DEMO Order (Market Buy INFY x1) ---")
        # print("IMPORTANT: The following order placement is an example.")
        # print("Ensure the tradingsymbol is correct and you understand the risk.")
        # confirm = input("Type 'yes' to place a buy order for 1 share of INFY at market price: ")
        # if confirm.lower() == 'yes':
        #     try:
        #         order_details = {
        #             "variety": "regular",
        #             "exchange": "NSE",
        #             "tradingsymbol": "INFY-EQ", # Ensure this is a valid symbol for your account
        #             "transaction_type": "BUY",
        #             "quantity": 1,
        #             "product": "CNC", # Cash and Carry (for equity delivery)
        #             "order_type": "MARKET"
        #         }
        #         order_response = client.place_order(**order_details)
        #         log.info(f"Order placement response: {order_response}")
        #         if order_response and order_response.get("data", {}).get("order_id"):
        #             log.info(f"Order ID: {order_response['data']['order_id']}")
        #         else:
        #             log.warning("Order placed but order_id not found in response or response was unexpected.")
        #     except OrderException as oe:
        #         log.error(f"OrderException: {oe.message} (Code: {oe.code})")
        #     except KiteException as ke:
        #         log.error(f"KiteException during order placement: {ke.message} (Code: {ke.code})")
        # else:
        #     log.info("Order placement skipped by user.")


        log.info("\nExample script finished successfully.")

    except DataException as e: # Catch config issues if they occur post-init
        log.error(f"Data/Configuration Error: {e}")
    except TokenException as e:
        log.error(f"Token Error: {e.message}. Your access token might be invalid or expired. Please try re-authenticating.")
    except KiteException as e:
        log.error(f"A Kite API Error occurred: {e.message} (Code: {e.code})")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True) # exc_info=True for traceback

if __name__ == "__main__":
    run_example()
