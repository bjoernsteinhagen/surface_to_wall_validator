"""This module contains the function's business logic.

Use the automation_context module to wrap your function in an Automate context helper.
"""

from collections import defaultdict
from typing import Optional
from pydantic import Field, SecretStr
from speckle_automate import (
    AutomateBase,
    AutomationContext,
    execute_automate_function,
)
from specklepy.objects.units import Units
from flatten import flatten_base

from models.etabs import validate_etabs_source, extract_analytical_surfaces
from models.revit import get_revit_model

class FunctionInputs(AutomateBase):
    """These are function author-defined values.

    Automate will make sure to supply them matching the types specified here.
    Please use the pydantic model schema to define your inputs:
    https://docs.pydantic.dev/latest/usage/models/
    """

    revit_model_name: str = Field(
        ...,
        title="Branch name of the Revit model to check the structural model against.",
        )
    
    buffer_size: float = Field(
        default=0.01,
        title="Buffer size for the Revit walls (tolerance)",
        description="Specify the size of the buffered mesh. \
            The vertices of the 3D mesh of the wall(s) are translated along the normals of each face with this value.",
            json_schema_extra={"readOnly" : True,
                               },
    )

    buffer_unit: str = Field(
        default=Units.m,
        title="Buffer Unit",
        description="Unit of the buffer size value.",
        json_schema_extra={
            "examples": ["mm", "cm", "m"],
            "readOnly" : True
        },
    )


def automate_function(
    automate_context: AutomationContext,
    function_inputs: FunctionInputs,
) -> None:
    """This is an example Speckle Automate function.

    Args:
        automate_context: A context-helper object that carries relevant information
            about the runtime context of this function.
            It gives access to the Speckle project data that triggered this run.
            It also has convenient methods for attaching result data to the Speckle model.
        function_inputs: An instance object matching the defined schema.
    """
    # The context provides a convenient way to receive the triggering version.
    etabs_commit = automate_context.receive_version()
    revit_commit = get_revit_model(automate_context, function_inputs.revit_model_name)

    if validate_etabs_source(etabs_commit):
        analytical_surfaces = extract_analytical_surfaces(etabs_model=getattr(etabs_commit, "@Model"))
        print(analytical_surfaces)

    objects_with_forbidden_speckle_type = [
        b
        for b in flatten_base(etabs_commit["@Model"])
        if b.speckle_type == function_inputs.forbidden_speckle_type
    ]
    count = len(objects_with_forbidden_speckle_type)

    if count > 0:
        # This is how a run is marked with a failure cause.
        automate_context.attach_error_to_objects(
            category="Forbidden speckle_type"
            f" ({function_inputs.forbidden_speckle_type})",
            object_ids=[o.id for o in objects_with_forbidden_speckle_type if o.id],
            message="This project should not contain the type: "
            f"{function_inputs.forbidden_speckle_type}",
        )
        automate_context.mark_run_failed(
            "Automation failed: "
            f"Found {count} object that have one of the forbidden speckle types: "
            f"{function_inputs.forbidden_speckle_type}"
        )

        # Set the automation context view to the original model/version view
        # to show the offending objects.
        automate_context.set_context_view()

    else:
        automate_context.mark_run_success("No forbidden types found.")

    # If the function generates file results, this is how it can be
    # attached to the Speckle project/model
    # automate_context.store_file_result("./report.pdf")


def automate_function_without_inputs(automate_context: AutomationContext) -> None:
    """A function example without inputs.

    If your function does not need any input variables,
     besides what the automation context provides,
     the inputs argument can be omitted.
    """
    pass

# make sure to call the function with the executor
if __name__ == "__main__":
    # NOTE: always pass in the automate function by its reference; do not invoke it!

    # Pass in the function reference with the inputs schema to the executor.
    execute_automate_function(automate_function, FunctionInputs)

    # If the function has no arguments, the executor can handle it like so
    #execute_automate_function(automate_function_without_inputs)
