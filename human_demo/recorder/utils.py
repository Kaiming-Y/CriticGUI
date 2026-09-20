from datetime import datetime

def manhattan_distance(list1, list2):
    """Compute the Manhattan distance between two lists."""
    return sum(abs(np.array(list1) - np.array(list2)))

def read_file_to_list(filepath):
    try:
        # Open and read the file
        with open(filepath, 'r', encoding='utf-8') as file:
            # Read lines into a list, stripping newline characters
            
            lines = [line.strip() for line in file]
            
        return lines
    except Exception as e:
        # Return the error message if any
        return f"Error reading file: {str(e)}"

def transform_time_format(original_string):
    # Convert to datetime object
    datetime_object = datetime.strptime(
        original_string, "%Y-%m-%d %H:%M:%S.%f")

    # Format datetime object to new format
    new_format = datetime_object.strftime("%Y%m%d_%H%M%S")

    return new_format
