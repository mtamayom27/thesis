import numpy as np


class EnvironmentalContext:
    def __init__(self, elements=None):
        self.elements = elements if elements else []

    def add_element(self, element, position):
        self.elements.append((element, position))

    def compare(self, other_context):
        similarity = 0
        for e1, p1 in self.elements:
            for e2, p2 in other_context.elements:
                if e1 == e2:
                    distance = np.linalg.norm(np.array(p1) - np.array(p2))
                    similarity += max(0, 1 - distance / 15)
        return similarity

def fetch_environmental_context():
    context = EnvironmentalContext()
    for obj_id, shape in objects:
        pos, _ = p.getBasePositionAndOrientation(obj_id)
        context.add_element(shape, pos[:2])  # Use x, y positions only
    return context
