import json

def process_hotkey_actions(normalized_actions):
    """
    Process actions in normalized_actions where action_type is "hotkey":
      - If value does not contain '+', treat it as a single key and convert action_type to "press"
      - For key combinations, convert each part to lowercase and join with '+'
    
    Processing rules:
      - If the key starts with "Key.", remove the prefix and convert to lowercase
      - Otherwise, convert the whole key to lowercase directly
    
    Returns the processed list of actions.
    """
    def standardize_key(key):
        if key.startswith("Key."):
            return key[4:].strip().lower()
        return key.strip().lower()
    
    new_actions = []
    for action in normalized_actions:
        if action.get("action_type") == "hotkey":
            key_val = action.get("value", "")
            if '+' not in key_val:
                # Single key: change to press type, and convert to lowercase
                action["action_type"] = "press"
                action["value"] = standardize_key(key_val)
            else:
                # Combination: split by '+', convert each to lowercase, and rejoin
                parts = [standardize_key(part) for part in key_val.split('+')]
                action["value"] = '+'.join(parts)
        new_actions.append(action)
    return new_actions

def split_ctrl_scroll(parsed_logs):
    """
    Split all logs in parsed_logs where Action is "hotkey" and Key is "ctrl+scroll" into 3 separate records:
      1. keydown: represents pressing the Ctrl key
      2. scroll: represents the scroll action (preserving Position and Delta)
      3. keyup: represents releasing the Ctrl key

    For the split records:
      - keydown and keyup have Key set to "ctrl", and Position/Delta set to None
      - scroll retains the original Position and Delta, with Action set to "scroll"

    Args:
      parsed_logs: list of dict, original parsed log records

    Returns:
      A new list of parsed_logs including the split ctrl+scroll records
    """
    new_logs = []
    for log in parsed_logs:
        if log and log.get("Action") == "hotkey" and log.get("Key", "").lower() == "ctrl+scroll":
            keydown = {
                "timestamp": log.get("timestamp"),
                "Action": "keydown",
                "Key": "ctrl",
                "Position": None,
                "Delta": None,
                "Folder": log.get("Folder"),
                "end_timestamp": log.get("timestamp")
            }
            scroll = {
                "timestamp": log.get("timestamp"),
                "Action": "scroll",
                "Key": None,
                "Position": log.get("Position"),
                "Delta": log.get("Delta"),
                "Folder": log.get("Folder"),
                "end_timestamp": log.get("timestamp")
            }
            keyup = {
                "timestamp": log.get("end_timestamp") or log.get("timestamp"),
                "Action": "keyup",
                "Key": "ctrl",
                "Position": None,
                "Delta": None,
                "Folder": log.get("Folder"),
                "end_timestamp": log.get("end_timestamp") or log.get("timestamp")
            }
            new_logs.extend([keydown, scroll, keyup])
        else:
            new_logs.append(log)
    return new_logs

def normalize_move_action(log):
    """
    Normalize move action:
      - action_type is always "move to"
      - use end_position if present, otherwise Position
      - value is set to None
    """
    norm = {}
    norm["action_type"] = "move to"
    pos = log.get("end_position") or log.get("Position")
    if pos is not None and isinstance(pos, list):
        pos = tuple(pos)
    norm["position"] = pos
    norm["value"] = None
    return norm

def normalize_drag_action(log):
    """
    Normalize drag action:
      - action_type is always "drag to"
      - use end_position if present, otherwise Position
      - value is set to None
    """
    norm = {}
    norm["action_type"] = "drag to"
    pos = log.get("end_position") or log.get("Position")
    if pos is not None and isinstance(pos, list):
        pos = tuple(pos)
    norm["position"] = pos
    norm["value"] = None
    return norm

def normalize_click_action(log):
    """
    Normalize click or right click action:
      - action_type is preserved ("click" or "right click")
      - position is taken from Position and converted to tuple
      - value is set to None
    """
    norm = {}
    action_type = log.get("Action")
    if action_type == "click":
        norm["action_type"] = "left click"
    elif action_type == "right click":
        norm["action_type"] = "right click"
    else:
        norm["action_type"] = action_type
    pos = log.get("Position")
    if pos is not None and isinstance(pos, list):
        pos = tuple(pos)
    norm["position"] = pos
    norm["value"] = None
    return norm

def normalize_scroll_action(log):
    """
    Normalize scroll action:
      - action_type is "scroll"
      - value is Delta (converted to tuple)
      - position is Position (converted to tuple)
    """
    norm = {}
    norm["action_type"] = "scroll"
    delta = log.get("Delta")
    if delta is not None and isinstance(delta, list):
        delta = tuple(delta)
    norm["value"] = delta
    pos = log.get("Position")
    if pos is not None and isinstance(pos, list):
        pos = tuple(pos)
    norm["position"] = pos
    return norm

def normalize_keyboard_action(log):
    """
    Normalize keyboard-related actions (hotkey, pressed_and_released_key, keydown, keyup, write):
      - action_type is the original Action
      - value is the Key
      - position is set to None
    """
    norm = {}
    norm["action_type"] = log.get("Action")
    norm["value"] = log.get("Key")
    norm["position"] = None
    return norm

def normalize_default_action(log):
    """
    Default normalization:
      - action_type is the original Action
      - position is converted to tuple if present
      - value is Key or Delta
    """
    norm = {}
    norm["action_type"] = log.get("Action")
    pos = log.get("Position")
    if pos is not None and isinstance(pos, list):
        pos = tuple(pos)
    norm["position"] = pos
    norm["value"] = log.get("Key") or log.get("Delta")
    return norm

def normalize_single_action(log):
    """
    Normalize a single log entry by dispatching to the appropriate normalization function based on Action field.
    """
    action = log.get("Action")
    if action == "move":
        return normalize_move_action(log)
    elif action == "drag":
        return normalize_drag_action(log)
    elif action in ["click", "right click"]:
        return normalize_click_action(log)
    elif action == "scroll":
        return normalize_scroll_action(log)
    elif action in ["hotkey", "pressed_and_released_key", "keydown", "keyup", "write"]:
        return normalize_keyboard_action(log)
    else:
        return normalize_default_action(log)

def normalize_logs(parsed_logs):
    """
    Apply normalize_single_action to each log in parsed_logs and return a list of normalized actions.
    """
    return [normalize_single_action(log) for log in parsed_logs]
