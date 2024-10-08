"""Run integration tests with a speckle server."""
import secrets
import string

import pytest
from gql import gql
from speckle_automate import (
    AutomationRunData,
    AutomationStatus,
    run_function,
    AutomationContext,
)
from specklepy.api.client import SpeckleClient
from specklepy.objects.base import Base

from main import FunctionInputs, automate_function, get_reference_model


def crypto_random_string(length: int) -> str:
    """Generate a semi crypto random string of a given length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def register_new_automation(
        project_id: str,
        model_id: str,
        speckle_client: SpeckleClient,
        automation_id: str,
        automation_name: str,
        automation_revision_id: str,
):
    """Register a new automation in the speckle server."""
    query = gql(
        """
        mutation CreateAutomation(
            $projectId: String! 
            $modelId: String! 
            $automationName: String!
            $automationId: String! 
            $automationRevisionId: String!
        ) {
                automationMutations {
                    create(
                        input: {
                            projectId: $projectId
                            modelId: $modelId
                            automationName: $automationName 
                            automationId: $automationId
                            automationRevisionId: $automationRevisionId
                        }
                    )
                }
            }
        """
    )
    params = {
        "projectId": project_id,
        "modelId": model_id,
        "automationName": automation_name,
        "automationId": automation_id,
        "automationRevisionId": automation_revision_id,
    }
    speckle_client.httpclient.execute(query, params)


@pytest.fixture()
def speckle_token(request) -> str:
    return request.config.SPECKLE_TOKEN


@pytest.fixture()
def speckle_server_url(request) -> str:
    """Provide a speckle server url for the test suite, default to localhost."""
    return request.config.SPECKLE_SERVER_URL


@pytest.fixture()
def test_client(speckle_server_url: str, speckle_token: str) -> SpeckleClient:
    """Initialize a SpeckleClient for testing."""
    test_client = SpeckleClient(
        speckle_server_url, speckle_server_url.startswith("https")
    )
    test_client.authenticate_with_token(speckle_token)
    return test_client


@pytest.fixture()
def test_object() -> Base:
    """Create a Base model for testing."""
    root_object = Base()
    root_object.foo = "bar"
    return root_object


@pytest.fixture()
# fixture to mock the AutomationRunData that would be generated by a full Automation Run
def fake_automation_run_data(request, test_client: SpeckleClient) -> AutomationRunData:
    server_url = request.config.SPECKLE_SERVER_URL
    project_id = "7d8e96669a"
    model_id = "efeb71387b"

    function_name = "Clash Test"

    automation_id = crypto_random_string(10)
    automation_name = "Long running clash test"
    automation_revision_id = crypto_random_string(10)

    register_new_automation(
        project_id,
        model_id,
        test_client,
        automation_id,
        automation_name,
        automation_revision_id,
    )

    fake_run_data = AutomationRunData(
        project_id=project_id,
        model_id=model_id,
        branch_name="main",
        version_id="2eb06c1034",
        speckle_server_url=server_url,
        # These ids would be available with a valid registered Automation definition.
        automation_id=automation_id,
        automation_revision_id=automation_revision_id,
        automation_run_id=crypto_random_string(12),
        # These ids would be available with a valid registered Function definition. Can also be faked.
        function_id="12345",
        function_name=function_name,
        function_logo=None,
    )

    return fake_run_data


def test_function_run(fake_automation_run_data: AutomationRunData, speckle_token: str):
    """Run an integration test for the automate function."""
    context = AutomationContext.initialize(fake_automation_run_data, speckle_token)

    automate_sdk = run_function(
        context,
        automate_function,
        FunctionInputs(
            tolerance=0.1, tolerance_unit="mm", static_model_name="simple beams"
        ),
    )

    assert automate_sdk.run_status == AutomationStatus.SUCCEEDED


@pytest.fixture
def context(fake_automation_run_data: AutomationRunData, speckle_token: str):
    return AutomationContext.initialize(fake_automation_run_data, speckle_token)


def test_non_existent_model(context, test_client: SpeckleClient):
    with pytest.raises(
            Exception, match="The static model named does not exist, skipping the function."
    ):
        get_reference_model(context, "Fake Name")


def test_model_with_no_versions(context, test_client: SpeckleClient):
    with pytest.raises(
            Exception, match="The static model has no versions, skipping the function."
    ):
        get_reference_model(context, "blank")


def test_same_as_changed_model(context, test_client: SpeckleClient):
    with pytest.raises(
            Exception,
            match="The static model is the same as the changed model, skipping the function.",
    ):
        get_reference_model(context, "clash simple")


def test_valid_reference_model(context, test_client: SpeckleClient):
    reference_model = get_reference_model(context, "simple beams")
    assert reference_model is not None