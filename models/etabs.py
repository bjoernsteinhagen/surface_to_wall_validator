import numpy as np

def validate_etabs_source(version_root_object):
    try:
        
        # Try and access the @Model element
        model_element = version_root_object['@Model']
        
        # Check if @Model exists
        if model_element is None:
            return False
        
        # Check the speckle_type of @Model
        if getattr(model_element, 'speckle_type', None) != "Objects.Structural.Analysis.Model":
            return False

    except KeyError:
        return False
    
    else:
        return True

class AnalyticalSurface:
    def __init__(self, points, id):
        self.points = np.array(points)  # Numpy array of 3D points
        self.id = id
        self.bounds = np.array([np.min(points, axis=0), np.max(points, axis=0)])

def create_analytical_surface(surface):
    # Create an AnalyticalSurface object from an element
    vertices_array = np.array(surface.displayValue[0].vertices).reshape(-1, 3)
    return AnalyticalSurface(vertices_array, surface.id)

def extract_analytical_surfaces(etabs_model):
    # Extract elements from the model
    elements = getattr(etabs_model, "elements", [])
    
    # Use a set for tracking application IDs to ensure uniqueness
    application_ids = set()
    
    # Create AnalyticalSurface objects for unique elements of type "Element2D"
    analytical_surfaces = [
        create_analytical_surface(element)
        for element in elements
        if "Element2D" in element.speckle_type and element.applicationId not in application_ids
        and not application_ids.add(element.applicationId)
    ]

    return analytical_surfaces
