from specklepy.api import operations
from specklepy.api.models import Branch
from specklepy.objects import Base
from specklepy.objects.other import Transform
from specklepy.transports.server import ServerTransport
from speckle_automate import AutomationContext
from typing import Optional

def get_revit_model(
    automate_context: AutomationContext, static_model_name: str
) -> tuple[Base, Optional[str], Optional[str]]:
    # the static reference model will be retrieved from the project using model name stored in the inputs
    speckle_client = automate_context.speckle_client
    project_id = automate_context.automation_run_data.project_id
    remote_transport = ServerTransport(
        automate_context.automation_run_data.project_id, speckle_client
    )

    model: Branch = speckle_client.branch.get(
        project_id, static_model_name, commits_limit=1
    )  # get the latest commit of the static model

    if not model:
        raise Exception("The static model named does not exist, skipping the function.")

    reference_model_commits = model.commits.items

    if not reference_model_commits:
        raise Exception("The static model has no versions, skipping the function.")

    latest_reference_model_id = model.id

    latest_reference_model_version_object = reference_model_commits[0].referencedObject

    if latest_reference_model_id == automate_context.automation_run_data.model_id:
        raise Exception(
            "The static model is the same as the changed model, skipping the function."
        )

    latest_reference_model_version = operations.receive(
        latest_reference_model_version_object,
        remote_transport,
    )  # receive the static model

    return latest_reference_model_version, model.id, reference_model_commits[0].id