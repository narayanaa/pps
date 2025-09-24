# Global index counter
element_counter = 0


def generate_unique_id() -> int:
    global element_counter
    element_counter += 1
    return element_counter
