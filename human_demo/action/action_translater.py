def manhattan_distance(pos1, pos2):
    """Calculate Manhattan distance between two coordinates."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def translate_move(act):
    """Translate 'move to' into pyautogui.moveTo(x, y) using the target position."""
    pos = act.get("position")
    if pos:
        return [f"pyautogui.moveTo({pos[0]}, {pos[1]})"]
    return []

def translate_click(act):
    """Translate 'click' into pyautogui.click(x, y) using the target position."""
    pos = act.get("position")
    if pos:
        return f"pyautogui.click({pos[0]}, {pos[1]})"
    return "# click action missing position"

def translate_right_click(act):
    """Translate 'right click' into pyautogui.click(x, y, button='right')."""
    pos = act.get("position")
    if pos:
        return f"pyautogui.click({pos[0]}, {pos[1]}, button='right')"
    return "# right click action missing position"

def translate_drag(act):
    """Translate 'drag to' into pyautogui.dragTo(x, y, button='left')."""
    pos = act.get("position")
    if pos:
        return [f"pyautogui.dragTo({pos[0]}, {pos[1]}, button='left')"]
    return []

def translate_keydown(act):
    """Translate 'keydown' into pyautogui.keyDown(key)."""
    key_val = act.get("value")
    if key_val:
        return [f"pyautogui.keyDown('{key_val}')"]
    return []

def translate_keyup(act):
    """Translate 'keyup' into pyautogui.keyUp(key)."""
    key_val = act.get("value")
    if key_val:
        return [f"pyautogui.keyUp('{key_val}')"]
    return []

def translate_press(act):
    """Translate 'press' into pyautogui.press(key)."""
    key_val = act.get("value")
    if key_val:
        return [f"pyautogui.press('{key_val}')"]
    return []

def translate_hotkey(act):
    """Translate 'hotkey' into pyautogui.hotkey(...), splitting the key combination."""
    key_val = act.get("value")
    if key_val:
        parts = key_val.split('+')
        parts_str = ', '.join(f"'{p}'" for p in parts)
        return [f"pyautogui.hotkey({parts_str})"]
    return []

def escape_text_for_code(text):
    """
    Escape a string by wrapping it in single quotes and escaping any single quotes inside.
    For example, input: Hello, 'world'! -> output: 'Hello, \'world\'!'
    """
    return repr(text)

def translate_write(act):
    """Translate 'write' into pyautogui.write(text)."""
    text = act.get("value")
    if text:
        escaped_text = escape_text_for_code(text)
        return [f"pyautogui.write({escaped_text})"]
    return []

def translate_scroll(act):
    """
    Translate 'scroll': 
    If delta indicates horizontal scrolling (dx != 0), use pyautogui.hscroll().
    If vertical (dy != 0), use pyautogui.scroll().
    Optionally include position if present.
    """
    delta = act.get("value")
    pos = act.get("position")
    if delta and isinstance(delta, (list, tuple)):
        dx, dy = delta
        if dx != 0:
            if pos:
                return [f"pyautogui.hscroll({dx}, x={pos[0]}, y={pos[1]})"]
            else:
                return [f"pyautogui.hscroll({dx})"]
        elif dy != 0:
            if pos:
                return [f"pyautogui.scroll({dy}, x={pos[0]}, y={pos[1]})"]
            else:
                return [f"pyautogui.scroll({dy})"]
    return []

def translate_click_block(actions, i, click_threshold):
    """
    Merge consecutive click or right-click events starting at index i
    if their positions are close (under click_threshold).
    Returns the generated code lines and the next index to process.
    Uses the 'clicks' parameter of pyautogui.click to perform multiple clicks.
    """
    act = actions[i]
    act_type = act.get("action_type")
    pos = act.get("position")
    count = 1
    j = i + 1
    while j < len(actions) and actions[j].get("action_type") == act_type:
        pos_next = actions[j].get("position")
        if pos and pos_next and manhattan_distance(pos, pos_next) < click_threshold:
            count += 1
            j += 1
        else:
            break
    code_lines = []
    if act_type == "right click":
        if count >= 2:
            code_lines.append(f"pyautogui.click({pos[0]}, {pos[1]}, button='right', clicks={count}, interval=0.25)")
        else:
            code_lines.append(f"pyautogui.click({pos[0]}, {pos[1]}, button='right')")
    else:
        if count >= 2:
            code_lines.append(f"pyautogui.click({pos[0]}, {pos[1]}, clicks={count}, interval=0.25)")
        else:
            code_lines.append(f"pyautogui.click({pos[0]}, {pos[1]})")
    return code_lines, j

def translate_scroll_block(actions, i):
    """
    Merge consecutive scroll events with the same direction.
    Accumulate their deltas and generate a single scroll or hscroll command.
    Returns the code lines and the next index to process.
    """
    act = actions[i]
    if act.get("action_type") != "scroll":
        return [], i
    delta = act.get("value")
    pos = act.get("position")
    total_dx, total_dy = (delta if delta else (0, 0))
    j = i + 1
    while j < len(actions) and actions[j].get("action_type") == "scroll":
        next_delta = actions[j].get("value")
        if next_delta and isinstance(next_delta, (list, tuple)):
            if total_dy != 0 and total_dy * next_delta[1] > 0:
                total_dy += next_delta[1]
                j += 1
            elif total_dx != 0 and total_dx * next_delta[0] > 0:
                total_dx += next_delta[0]
                j += 1
            else:
                break
        else:
            break
    if total_dx != 0:
        code_line = f"pyautogui.hscroll({total_dx}, x={pos[0]}, y={pos[1]})" if pos else f"pyautogui.hscroll({total_dx})"
    else:
        code_line = f"pyautogui.scroll({total_dy}, x={pos[0]}, y={pos[1]})" if pos else f"pyautogui.scroll({total_dy})"
    return [code_line], j

def translate_write_block(actions, i):
    """
    Merge consecutive 'write' actions into one pyautogui.write call.
    Returns the code lines and the next index to process.
    """
    act = actions[i]
    if act.get("action_type") != "write":
        return [], i
    text = act.get("value", "")
    j = i + 1
    while j < len(actions) and actions[j].get("action_type") == "write":
        text += actions[j].get("value", "")
        j += 1
    escaped_text = escape_text_for_code(text)
    code_line = f"pyautogui.write({escaped_text})"
    return [code_line], j

def translate_press_block(actions, i):
    """
    Merge consecutive "press" events with the same key.
    Returns a list of generated code lines and the next unprocessed index.
    Uses pyautogui.press(key, presses=n) to perform multiple presses in one call.
    """
    act = actions[i]
    key_val = act.get("value")
    count = 1
    j = i + 1
    while j < len(actions):
        next_act = actions[j]
        if next_act.get("action_type") == "press" and next_act.get("value") == key_val:
            count += 1
            j += 1
        else:
            break
    if count > 1:
        code_line = f"pyautogui.press('{key_val}', presses={count})"
    else:
        code_line = f"pyautogui.press('{key_val}')"
    return [code_line], j

def translate_hotkey_block(actions, i):
    """
    Merge consecutive keydown/keyup pairs into a single pyautogui.hotkey call.
    Returns the code lines and the next index to process.
    """
    if actions[i].get("action_type") != "keydown":
        return [], i
    keys_down = []
    j = i
    while j < len(actions) and actions[j].get("action_type") == "keydown":
        keys_down.append(actions[j].get("value"))
        j += 1
    keys_up = []
    while j < len(actions) and actions[j].get("action_type") == "keyup":
        keys_up.append(actions[j].get("value"))
        j += 1
    if keys_down and keys_up == list(reversed(keys_down)):
        parts_str = ', '.join(f"'{k}'" for k in keys_down)
        code_line = f"pyautogui.hotkey({parts_str})"
        return [code_line], j
    else:
        result = translate_keydown(actions[i])
        return result, i + 1

def translate_single_action(act):
    """
    Translate a single normalized action to corresponding pyautogui code.
    Dispatch based on action_type.
    """
    action_type = act.get("action_type")
    if action_type == "move to":
        result = translate_move(act)
        return result[0] if result else ""
    elif action_type == "drag to":
        result = translate_drag(act)
        return result[0] if result else ""
    elif action_type == "left click" or action_type == "click":
        return translate_click(act)
    elif action_type == "right click":
        return translate_right_click(act)
    elif action_type == "keydown":
        result = translate_keydown(act)
        return result[0] if result else ""
    elif action_type == "keyup":
        result = translate_keyup(act)
        return result[0] if result else ""
    elif action_type == "press":
        result = translate_press(act)
        return result[0] if result else ""
    elif action_type == "hotkey":
        result = translate_hotkey(act)
        return result[0] if result else ""
    elif action_type == "write":
        result = translate_write(act)
        return result[0] if result else ""
    elif action_type == "scroll":
        result = translate_scroll(act)
        return result[0] if result else ""
    else:
        return f"# Unrecognized action: {act}"

def translate_actions(actions, click_threshold=10):
    """
    Translate an action sequence into pyautogui code.
    Supports context-aware merging of:
      - click blocks (using clicks parameter)
      - scroll blocks (accumulating deltas)
      - write blocks (concatenating text)
      - hotkey blocks (merging keydown/keyup pairs)
      - press blocks (merging consecutive press events)
    """
    code_lines = []
    i = 0
    while i < len(actions):
        act = actions[i]
        act_type = act.get("action_type")
        if act_type in ["left click", "right click", "click"]:
            lines, new_index = translate_click_block(actions, i, click_threshold)
            code_lines.extend(lines)
            i = new_index
        elif act_type == "move to":
            code_lines.extend(translate_move(act))
            i += 1
        elif act_type == "drag to":
            code_lines.extend(translate_drag(act))
            i += 1
        elif act_type == "keydown":
            lines, new_index = translate_hotkey_block(actions, i)
            code_lines.extend(lines)
            i = new_index
        elif act_type == "keyup":
            code_lines.extend(translate_keyup(act))
            i += 1
        elif act_type == "press":
            lines, new_index = translate_press_block(actions, i)
            code_lines.extend(lines)
            i = new_index
        elif act_type == "hotkey":
            code_lines.extend(translate_hotkey(act))
            i += 1
        elif act_type == "write":
            lines, new_index = translate_write_block(actions, i)
            code_lines.extend(lines)
            i = new_index
        elif act_type == "scroll":
            lines, new_index = translate_scroll_block(actions, i)
            code_lines.extend(lines)
            i = new_index
        else:
            code_lines.append(f"# Unrecognized action: {act}")
            i += 1
    return code_lines
