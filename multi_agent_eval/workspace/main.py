"""Main application module."""

def process_data(data):
    """Process input data."""
    # TODO: Implement validation
    result = transform_data(data)
    return result

def transform_data(data):
    """Transform the data."""
    # Basic transformation
    return data.upper() if isinstance(data, str) else str(data)

if __name__ == "__main__":
    test_data = "hello world"
    print(process_data(test_data))
