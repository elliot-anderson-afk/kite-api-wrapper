import os
import pytest
import configparser
import shutil

from kite_wrapper.config import KiteConfig
from kite_wrapper.exceptions import DataException

CONFIG_CONTENT = """
[Kite]
api_key = file_api_key
api_secret = file_api_secret
access_token = file_access_token
"""

TEST_CONFIG_PATH = "test_config.ini"


@pytest.fixture(autouse=True)
def manage_environment_variables():
    """Fixture to manage environment variables for tests."""
    original_env = {}
    vars_to_set = {
        "KITE_API_KEY": "env_api_key",
        "KITE_API_SECRET": "env_api_secret",
        "KITE_ACCESS_TOKEN": "env_access_token",
    }
    # Store original values and set new ones
    for var, value in vars_to_set.items():
        original_env[var] = os.environ.get(var)
        os.environ[var] = value

    vars_that_might_interfere = ["KITE_API_KEY", "KITE_API_SECRET", "KITE_ACCESS_TOKEN"]
    for var in vars_that_might_interfere:
        if var not in vars_to_set:
            original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    yield

    for var, value in original_env.items():
        if value is None:
            if var in os.environ:
                del os.environ[var]
        else:
            os.environ[var] = value


@pytest.fixture
def temp_config_file():
    """Creates a temporary config file for testing."""
    with open(TEST_CONFIG_PATH, "w") as f:
        f.write(CONFIG_CONTENT)
    yield TEST_CONFIG_PATH
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)


def test_init_with_direct_params():
    # Temporarily clear env vars that might be set by autouse fixture for this specific test case
    original_env_values = {
        k: os.environ.pop(k, None) for k in ["KITE_API_KEY", "KITE_API_SECRET", "KITE_ACCESS_TOKEN"]
    }
    config = KiteConfig(api_key="direct_key", api_secret="direct_secret", access_token="direct_token", config_path="non_existent.ini")
    assert config.get_api_key() == "direct_key"
    assert config.get_api_secret() == "direct_secret"
    assert config.get_access_token() == "direct_token"
    # Restore env vars
    for k, v in original_env_values.items():
        if v is not None:
            os.environ[k] = v


def test_load_from_env_vars(manage_environment_variables):
    config = KiteConfig(config_path="non_existent.ini") # Ensure no file interference
    assert config.get_api_key() == "env_api_key"
    assert config.get_api_secret() == "env_api_secret"
    assert config.get_access_token() == "env_access_token"


def test_load_from_file(temp_config_file, manage_environment_variables):
    os.environ.pop("KITE_API_KEY", None)
    os.environ.pop("KITE_API_SECRET", None)
    os.environ.pop("KITE_ACCESS_TOKEN", None)

    config = KiteConfig(config_path=temp_config_file)
    assert config.get_api_key() == "file_api_key"
    assert config.get_api_secret() == "file_api_secret"
    assert config.get_access_token() == "file_access_token"


def test_param_overrides_file(temp_config_file, manage_environment_variables):
    os.environ.pop("KITE_API_KEY", None)
    os.environ.pop("KITE_API_SECRET", None)
    os.environ.pop("KITE_ACCESS_TOKEN", None)

    config = KiteConfig(api_key="param_key", api_secret="param_secret", config_path=temp_config_file)
    assert config.get_api_key() == "param_key"
    assert config.get_api_secret() == "param_secret"
    assert config.get_access_token() == "file_access_token"


def test_param_overrides_env(manage_environment_variables):
    # Env vars are "env_api_key", "env_api_secret", "env_access_token"
    config = KiteConfig(api_key="param_key", access_token="param_token", config_path="non_existent.ini")
    assert config.get_api_key() == "param_key"
    assert config.get_api_secret() == "env_api_secret"
    assert config.get_access_token() == "param_token"


def test_env_overrides_file(temp_config_file, manage_environment_variables):
    # Env vars ("env_api_key", etc.) are set by fixture.
    # File vars ("file_api_key", etc.) are in temp_config_file.
    config = KiteConfig(config_path=temp_config_file)
    assert config.get_api_key() == "env_api_key"
    assert config.get_api_secret() == "env_api_secret"
    assert config.get_access_token() == "env_access_token"


def test_missing_api_key_secret_raises_exception(manage_environment_variables):
    os.environ.pop("KITE_API_KEY", None)
    os.environ.pop("KITE_API_SECRET", None)
    os.environ.pop("KITE_ACCESS_TOKEN", None)

    with pytest.raises(DataException) as excinfo:
        KiteConfig(config_path="non_existent_config.ini")
    assert "API key or secret is missing" in str(excinfo.value)

    # Test with only API key missing
    os.environ["KITE_API_SECRET"] = "some_secret_from_env" # KITE_API_KEY is already popped
    with pytest.raises(DataException) as excinfo_key_missing:
        KiteConfig(config_path="non_existent_config.ini")
    assert "API key or secret is missing" in str(excinfo_key_missing.value)
    os.environ.pop("KITE_API_SECRET", None) # Clean up for next part

    # Test with only API secret missing
    os.environ["KITE_API_KEY"] = "some_key_from_env" # KITE_API_SECRET is already popped
    with pytest.raises(DataException) as excinfo_secret_missing:
        KiteConfig(config_path="non_existent_config.ini")
    assert "API key or secret is missing" in str(excinfo_secret_missing.value)
    os.environ.pop("KITE_API_KEY", None) # Clean up


def test_set_and_get_access_token(temp_config_file):
    original_access_token_env = os.environ.pop("KITE_ACCESS_TOKEN", None)

    config = KiteConfig(api_key="test_key", api_secret="test_secret", config_path=temp_config_file)
    assert config.get_access_token() == "file_access_token"

    config.set_access_token("new_programmatic_token")
    assert config.get_access_token() == "new_programmatic_token"

    parser = configparser.ConfigParser()
    parser.read(temp_config_file)
    assert parser["Kite"]["access_token"] == "new_programmatic_token"

    if original_access_token_env is not None:
        os.environ["KITE_ACCESS_TOKEN"] = original_access_token_env


def test_set_access_token_no_config_file():
    original_access_token_env = os.environ.pop("KITE_ACCESS_TOKEN", None)

    config = KiteConfig(api_key="test_key", api_secret="test_secret", config_path="non_existent_config_for_test.ini")
    assert config.get_access_token() is None

    config.set_access_token("another_token")
    assert config.get_access_token() == "another_token"

    assert not os.path.exists("non_existent_config_for_test.ini")

    if original_access_token_env is not None:
        os.environ["KITE_ACCESS_TOKEN"] = original_access_token_env


@pytest.fixture
def manage_default_config_path_test(monkeypatch):
    mock_base_dir = os.path.join(os.getcwd(), "mock_user_temp_dir_for_default_path")
    mock_home = os.path.join(mock_base_dir, "home")
    expected_config_dir = os.path.join(mock_home, ".kite")
    expected_config_path = os.path.join(expected_config_dir, "config.ini")

    if os.path.exists(mock_base_dir):
        shutil.rmtree(mock_base_dir)

    os.makedirs(expected_config_dir, exist_ok=True)

    monkeypatch.setattr(os.path, "expanduser", lambda path: mock_home if path == "~" else path)

    yield expected_config_path, expected_config_dir, mock_base_dir

    if os.path.exists(mock_base_dir):
        shutil.rmtree(mock_base_dir)


def test_config_path_default_user_dir_file_exists(manage_default_config_path_test, manage_environment_variables):
    expected_config_path, _, _ = manage_default_config_path_test

    os.environ.pop("KITE_API_KEY", None)
    os.environ.pop("KITE_API_SECRET", None)
    os.environ.pop("KITE_ACCESS_TOKEN", None)

    with open(expected_config_path, "w") as f:
        f.write("[Kite]\napi_key = default_path_key\napi_secret = default_path_secret\naccess_token = default_path_token\n")

    config = KiteConfig()
    assert config.config_path == expected_config_path
    assert config.get_api_key() == "default_path_key"
    assert config.get_api_secret() == "default_path_secret"
    assert config.get_access_token() == "default_path_token"


def test_config_path_default_user_dir_file_not_exist(manage_default_config_path_test, manage_environment_variables):
    expected_config_path, _, _ = manage_default_config_path_test

    if os.path.exists(expected_config_path):
        os.remove(expected_config_path)

    # KITE_API_KEY etc are set by manage_environment_variables
    config = KiteConfig()
    assert config.config_path == expected_config_path
    assert config.get_api_key() == "env_api_key"
    assert config.get_api_secret() == "env_api_secret"
    assert config.get_access_token() == "env_access_token"


def test_config_file_missing_kite_section(temp_config_file, manage_environment_variables):
    with open(temp_config_file, "w") as f:
        f.write("[General]\nname=test")

    os.environ.pop("KITE_API_KEY", None)
    os.environ.pop("KITE_API_SECRET", None)
    os.environ.pop("KITE_ACCESS_TOKEN", None)

    with pytest.raises(DataException) as excinfo:
        KiteConfig(config_path=temp_config_file)
    assert "API key or secret is missing" in str(excinfo.value)

def test_str_representation(manage_environment_variables):
    # Clear relevant env vars for the first part of the test
    original_env_values = {
        k: os.environ.pop(k, None) for k in ["KITE_API_KEY", "KITE_API_SECRET", "KITE_ACCESS_TOKEN"]
    }

    config = KiteConfig(api_key="mykey", api_secret="mysecret", access_token="mytoken", config_path="non_existent.ini")
    assert "myke" in str(config)
    assert "myse" in str(config)
    assert "myto" in str(config)
    assert "None" not in str(config) # access_token is present

    config_no_token = KiteConfig(api_key="mykey", api_secret="mysecret", config_path="non_existent.ini")
    assert "myke" in str(config_no_token)
    assert "myse" in str(config_no_token)
    assert "access_token='None" in str(config_no_token) # Check for 'None' part for token

    # Restore original env values before the fixture's cleanup does its part
    for k, v in original_env_values.items():
        if v is not None:
            os.environ[k] = v

    # Test case where DataException might be raised due to missing keys
    # This part needs careful handling of environment for isolation
    temp_key = os.environ.pop("KITE_API_KEY", None) # remove key if exists
    temp_secret = os.environ.pop("KITE_API_SECRET", None) # remove secret if exists
    temp_token = os.environ.pop("KITE_ACCESS_TOKEN", None) # remove token if exists

    with pytest.raises(DataException):
        # This will fail as no keys are provided via param, env, or valid file
        KiteConfig(config_path="completely_non_existent_path.ini")
        # The str representation of such an object would ideally show Nones,
        # but object creation fails first.

    # Restore any popped global env vars to not affect other tests or fixture cleanup
    if temp_key is not None: os.environ["KITE_API_KEY"] = temp_key
    if temp_secret is not None: os.environ["KITE_API_SECRET"] = temp_secret
    if temp_token is not None: os.environ["KITE_ACCESS_TOKEN"] = temp_token
