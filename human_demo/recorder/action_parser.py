import os

import re

import sys

from datetime import datetime

import math

from human_demo.recorder.utils import transform_time_format, read_file_to_list, manhattan_distance

def remove_release_keys(parsed_logs):
    """
    过滤掉所有 Action 为 released_key 的日志记录，
    因为这些事件在合并后已经包含在 hotkey、write 或 pressed_and_released_key 中了。
    """
    return [log for log in parsed_logs if log.get("Action") != "released_key"]

def remove_exit_hotkey(parsed_logs):
    """过滤掉包含退出组合键（ctrl+shift+alt+q）的 hotkey 记录"""
    filtered = []
    for log in parsed_logs:
        if log.get("Action") == "hotkey":
            key_str = log.get("Key", "").lower()
            # 判断是否包含退出组合键标识：ctrl, shift, alt, F11（根据实际记录格式）
            if ("ctrl" in key_str and "shift" in key_str and ("f11" in key_str or "Key.f11" in key_str)):
                continue  # 过滤掉该记录
        filtered.append(log)
    return filtered

def preprocess_actions(log_filename):
    save_folder = os.path.dirname(log_filename)
    # Read the log file into a list
    actions = read_file_to_list(log_filename)
    parsed_logs = [item for line in actions if (item := parse_log_line(line, save_folder)) is not None]
    

    
    parsed_logs = merge_similar_consecutive_actions_with_delta(parsed_logs)
    parsed_logs = merge_move_actions(parsed_logs, threshold_ms=500, distance_threshold=10) # Set the time threshold between adjacent moves & distance threshold of single move
    parsed_logs = merge_scroll_actions(parsed_logs)
    parsed_logs = merge_ctrl_scroll_actions(parsed_logs)  # New merge function for ctrl+scroll actions
    parsed_logs = merge_click_release_actions(parsed_logs, threshold=10) # Set the distance threshold of drag
    parsed_logs = identify_enhanced_hotkey_sequences(parsed_logs)
    parsed_logs = merge_press_release_actions(parsed_logs)
    parsed_logs = handle_shift_hotkey(parsed_logs) # Convert hotkey only with shift to write
    parsed_logs = merge_character_special_and_backspace_keys(parsed_logs)
    parsed_logs = merge_click_move_release_actions(parsed_logs, threshold=10) # Set the distance threshold of drag

    # 过滤掉所有 released_key 记录
    parsed_logs = remove_release_keys(parsed_logs)
    # 最后过滤掉退出组合键的记录
    parsed_logs = remove_exit_hotkey(parsed_logs)

    parsed_logs = merge_final_scroll_events(parsed_logs)
    parsed_logs = merge_final_ctrl_scroll_events(parsed_logs)
    parsed_logs = merge_write_actions(parsed_logs, time_threshold_ms=2000) # Merge write actions

    return parsed_logs

def parse_log_line(log_line, save_folder):
    # Initialize the default log dictionary
    log_dict = {
        'timestamp': None,
        'Action': None,
        'Position': None,
        'Key': None,
        'Delta': None,
        'Folder': save_folder,
    }

    # Regular expression for parsing key action logs
    key_action_pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\-\d{6}) - Key (?P<key_action>pressed|released): (?P<key>.+)')

    # Regular expression for parsing mouse action logs
    mouse_action_pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\-\d{6}) - Mouse (?P<mouse_action>scroll|click|release|right click) at \((?P<position_x>-?\d+), (?P<position_y>-?\d+)\)( with delta \((?P<delta_x>[+-]?\d+), (?P<delta_y>[+-]?\d+)\))?'
    )

    # Move
    mouse_move_pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\-\d{6}) - Mouse move to \((?P<position_x>-?\d+), (?P<position_y>-?\d+)\)'
    )

    # Regular expression for detecting ctrl+scroll hotkey
    ctrl_scroll_pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\-\d{6}) - Hotkey \(ctrl\+scroll\) at \((?P<position_x>-?\d+), (?P<position_y>-?\d+)\) with delta \((?P<delta_x>[+-]?\d+), (?P<delta_y>[+-]?\d+)\)'
    )

    # Check for ctrl+scroll hotkey log
    ctrl_scroll_match = ctrl_scroll_pattern.search(log_line)
    if ctrl_scroll_match:
        details = ctrl_scroll_match.groupdict()
        log_dict.update({
            'timestamp': details['timestamp'],
            'Action': 'hotkey',  # Treat ctrl+scroll as a hotkey action
            'Position': (int(details['position_x']), int(details['position_y'])),
            'Key': 'ctrl+scroll',  # Add a Key field for the ctrl+scroll combination
            'Delta': (int(details['delta_x']), int(details['delta_y']))
        })
        return log_dict

    # Check if the log line is a key action
    key_match = key_action_pattern.search(log_line)
    if key_match:
        details = key_match.groupdict()
        log_dict.update({
            'timestamp': details['timestamp'],
            'Action': details['key_action'] + '_key',
            'Key': details['key'].strip("'")
        })

        # Use translate_hotkey to convert the Key field to its real representation
        log_dict = translate_hotkey(log_dict)  # Translate the key if it's a hotkey

        return log_dict

    # Check if the log line is a mouse action
    mouse_match = mouse_action_pattern.search(log_line)
    if mouse_match:
        details = mouse_match.groupdict()
        log_dict.update({
            'timestamp': details['timestamp'],
            'Action': details['mouse_action'],
            'Position': (int(details['position_x']), int(details['position_y']))
        })
        # Update delta if it exists
        if details['delta_x'] and details['delta_y']:
            log_dict['Delta'] = (int(details['delta_x']),
                                 int(details['delta_y']))
        return log_dict
    
    # Check for mouse move log
    move_match = mouse_move_pattern.search(log_line)
    if move_match:
        details = move_match.groupdict()
        log_dict.update({
            'timestamp': details['timestamp'],
            'Action': 'move',
            'Position': (int(details['position_x']), int(details['position_y'])),
            'Key': None  # Add Key field for move action
        })
        return log_dict

    # Return None if the line doesn't match expected patterns
    return log_dict if log_dict['timestamp'] else None

def merge_scroll_actions(parsed_logs):
    merged_logs = []
    previous_log = None

    for log in parsed_logs:
        # Check if current and previous actions are scrolls at the same position and the delta sign matches (we compare deltas by multiplying their y-components)
        if previous_log and log['Action'] == 'scroll' and previous_log['Action'] == 'scroll' and manhattan_distance(log['Position'], previous_log['Position']) < 20 and (log['Delta'][1] * previous_log['Delta'][1] >= 0):
            # Update the previous log instead of adding the current one
            # Update end_timestamp from current log
            previous_log['end_timestamp'] = log.get(
                'end_timestamp', log['timestamp'])
            # Accumulate Delta values
            previous_log['Delta'] = (
                previous_log['Delta'][0] + log['Delta'][0], previous_log['Delta'][1] + log['Delta'][1])
        else:
            # Add the previous log to the list before moving to the next
            if previous_log:
                merged_logs.append(previous_log)
            previous_log = log  # Reset the previous log for the next iteration

    # Make sure to add the last processed log if it exists
    if previous_log:
        merged_logs.append(previous_log)

    return merged_logs

def merge_ctrl_scroll_actions(parsed_logs):
    merged_logs = []
    previous_log = None

    for log in parsed_logs:
        # Check if the current log and the previous log are both 'ctrl+scroll' actions
        if previous_log and log['Action'] == 'hotkey' and previous_log['Action'] == 'hotkey' and 'ctrl+scroll' in log['Key'] and 'ctrl+scroll' in previous_log['Key']:
            # Check if the positions are close enough and the delta signs match (we use delta_y here)
            if manhattan_distance(log['Position'], previous_log['Position']) < 20 and (log['Delta'][1] * previous_log['Delta'][1] >= 0):
                # Merge the deltas and update the previous log
                previous_log['end_timestamp'] = log.get('end_timestamp', log['timestamp'])
                previous_log['Delta'] = (
                    previous_log['Delta'][0] + log['Delta'][0], previous_log['Delta'][1] + log['Delta'][1])
            else:
                # If they can't be merged, push the previous log to the list
                merged_logs.append(previous_log)
                previous_log = log  # Reset previous log to the current one
        else:
            # If not the same action, just add the previous one to the list and move forward
            if previous_log:
                merged_logs.append(previous_log)
            previous_log = log

    # Add the last processed log if it exists and assign the end_timestamp
    if previous_log:
        previous_log['end_timestamp'] = previous_log.get('end_timestamp', previous_log['timestamp'])
        merged_logs.append(previous_log)

    return merged_logs

def merge_move_actions(parsed_logs, threshold_ms=100, distance_threshold=10):
    """
    合并连续的鼠标 move 事件：
      - 如果相邻的 move 事件时间间隔小于 threshold_ms 毫秒，则认为属于同一次连续移动，
        将起始坐标保留为组内第一个事件的坐标，结束坐标取组内最后一次事件的坐标，
        同时更新起始和结束时间。
      - 如果合并后的 move 事件的起始和结束坐标变化小于 distance_threshold（默认为10），
        则不记录该 move 事件。
    """
    merged_logs = []
    move_group = None  # 用于保存当前连续的 move 组

    for log in parsed_logs:
        if log is None:
            continue
        if log.get('Action') == 'move':
            current_time = datetime.strptime(log['timestamp'], "%Y-%m-%d %H-%M-%S-%f")
            if move_group is None:
                # 新建一个 move 组，记录初始时间和位置
                move_group = log.copy()
                move_group['end_timestamp'] = log['timestamp']
                move_group['end_position'] = log['Position']  # 初始结束坐标与起始坐标一致
            else:
                # 比较当前 move 与上一个 move 的结束时间差
                last_time = datetime.strptime(move_group['end_timestamp'], "%Y-%m-%d %H-%M-%S-%f")
                time_diff = (current_time - last_time).total_seconds() * 1000  # 转换为毫秒
                if time_diff <= threshold_ms:
                    # 属于连续移动，更新组内结束时间和坐标
                    move_group['end_timestamp'] = log['timestamp']
                    move_group['end_position'] = log['Position']
                else:
                    duration = (datetime.strptime(move_group['end_timestamp'], "%Y-%m-%d %H-%M-%S-%f") -
                                datetime.strptime(move_group['timestamp'], "%Y-%m-%d %H-%M-%S-%f")).total_seconds()
                    move_group['duration'] = duration
                    # 计算起始与结束坐标之间的欧氏距离
                    start_pos = move_group['Position']
                    end_pos = move_group['end_position']
                    distance = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
                    if distance >= distance_threshold:
                        merged_logs.append(move_group)
                    move_group = log.copy()
                    move_group['end_timestamp'] = log['timestamp']
                    move_group['end_position'] = log['Position']
        else:
            # 如果当前日志不是 move 类型，先将待处理的 move 组写入，然后写入该日志
            if move_group is not None:
                duration = (datetime.strptime(move_group['end_timestamp'], "%Y-%m-%d %H-%M-%S-%f") -
                            datetime.strptime(move_group['timestamp'], "%Y-%m-%d %H-%M-%S-%f")).total_seconds()
                move_group['duration'] = duration  # 新增 duration 字段
                start_pos = move_group['Position']
                end_pos = move_group['end_position']
                distance = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
                if distance >= distance_threshold:
                    merged_logs.append(move_group)
                move_group = None
            merged_logs.append(log)
    
    # 循环结束后，如有未保存的 move 组，保存之
    if move_group is not None:
        duration = (datetime.strptime(move_group['end_timestamp'], "%Y-%m-%d %H-%M-%S-%f") -
                    datetime.strptime(move_group['timestamp'], "%Y-%m-%d %H-%M-%S-%f")).total_seconds()
        move_group['duration'] = duration  # 新增 duration 字段
        start_pos = move_group['Position']
        end_pos = move_group['end_position']
        distance = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
        if distance >= distance_threshold:
            merged_logs.append(move_group)
    
    return merged_logs

def merge_click_move_release_actions(parsed_logs, threshold=10):
    """
    合并序列中连续的点击（click/right click）后跟零个或多个 move，最后是 release 的事件，
    最终合并为一个单一的 drag（或 click）动作。
    
    参数:
      parsed_logs: 初步解析后的日志列表
      threshold: 像素距离阈值，用于判断是否为拖拽（distance >= threshold 认为是 drag）
    返回:
      合并后的日志列表
    """
    merged_logs = []
    i = 0
    while i < len(parsed_logs):
        current = parsed_logs[i]
        if current is None:
            i += 1
            continue
        if current.get('Action') in ['click', 'right click']:
            start_log = current
            j = i + 1
            # 跳过中间的 move 事件（如果有的话）
            while j < len(parsed_logs) and parsed_logs[j].get('Action') == 'move':
                j += 1
            if j < len(parsed_logs) and parsed_logs[j].get('Action') == 'release':
                release_log = parsed_logs[j]
                merged_log = start_log.copy()
                merged_log['end_timestamp'] = release_log['timestamp']
                merged_log['end_position'] = release_log['Position']
                # 判断从点击到释放的距离是否超过阈值，决定是否记为 drag
                x1, y1 = start_log.get('Position', (0, 0))
                x2, y2 = release_log.get('Position', (0, 0))
                distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                if distance >= threshold:
                    merged_log['Action'] = 'drag'
                else:
                    merged_log['Action'] = start_log['Action']  # 保持为 click
                merged_logs.append(merged_log)
                i = j + 1  # 跳过整个序列
                continue
        # 非 drag 序列直接添加
        merged_logs.append(current)
        i += 1
    return merged_logs

def merge_click_release_actions(parsed_logs, threshold=10):
    merged_logs = []
    for i in range(len(parsed_logs)):
        if i > 0 and parsed_logs[i]['Action'] == 'release' and (parsed_logs[i - 1]['Action'] == 'click' or parsed_logs[i - 1]['Action'] == 'right click' ):
            merged_log = parsed_logs[i - 1].copy()  # Copy the click action
            # Set end timestamp to release time
            merged_log['end_timestamp'] = parsed_logs[i]['timestamp']
            merged_log['end_position'] = parsed_logs[i]['Position']
            #  Mar 3 2024 modified
            x1,y1= parsed_logs[i]['Position']
            x2,y2= parsed_logs[i - 1]['Position']
            distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            # if parsed_logs[i]['Position'] != parsed_logs[i - 1]['Position']:
            if distance >= threshold:
                merged_log['Action'] = 'drag'

            merged_logs.pop()  # Remove the last click action added
            merged_logs.append(merged_log)  # Add the merged log
        else:
            merged_logs.append(parsed_logs[i])

    return merged_logs

def merge_press_release_actions(parsed_logs):
    # def merge_key_actions(parsed_logs):
    merged_logs = []
    temp_dict = {}  # Temporary dictionary to hold press and release events

    for log in parsed_logs:
        # Create a unique key for each action based on the key pressed
        if log['Key'] is None:
            merged_logs.append(log)
            continue

        unique_key = log['Key'] + \
            ('_press' if 'pressed' in log['Action'] else '_release')

        if 'pressed' in log['Action']:
            # Store the pressed key log temporarily
            temp_dict[unique_key] = log
        elif 'released' in log['Action']:
            # Check if corresponding press action exists
            press_unique_key = log['Key'] + '_press'
            if press_unique_key in temp_dict:
                # Merge press and release actions
                # Remove and get the press action
                merged_log = temp_dict.pop(press_unique_key)
                # Update action to show combined event
                merged_log['Action'] = 'pressed_and_released_key'
                # Add end timestamp from release action
                merged_log['end_timestamp'] = log['timestamp']
                merged_logs.append(merged_log)
            else:
                # If no corresponding press action, just add release action
                merged_logs.append(log)
        else:
            # If not a press or release action, add directly to the merged logs
            merged_logs.append(log)

    # Add any remaining pressed keys that were not released
    for remaining_log in temp_dict.values():
        merged_logs.append(remaining_log)

    return merged_logs

def merge_character_special_and_backspace_keys(parsed_logs):
    merged_logs = []
    # Define special keys that can be merged with their corresponding string values
    mergeable_keys = {
        'Key.space': ' ',
        # 'Key.enter': '\n',
        # 'Key.backspace' will be handled separately
    }

    for i, log in enumerate(parsed_logs):
        if log['Action'] == 'pressed_and_released_key':
            # Determine if the key is a character, a mergeable special key, or a non-mergeable special key
            actual_key = mergeable_keys.get(
                log['Key'], log['Key']) if log['Key'] in mergeable_keys else log['Key']
            if len(actual_key) == 1 or actual_key in mergeable_keys.values():
                # Handle as write action
                append_key_to_write_action(log, merged_logs, actual_key)
            elif log['Key'] == 'Key.backspace':
                # Special handling for backspace
                if merged_logs and merged_logs[-1]['Action'] == 'write' and merged_logs[-1]['Key']:
                    # If there is a preceding character, append backspace
                    append_key_to_write_action(log, merged_logs, '\b')
                else:
                    # Otherwise, handle as hotkey
                    append_new_action(log, merged_logs, 'hotkey')
            else:
                # For other special keys like 'Ctrl', 'Shift', etc., mark them as hotkey
                append_new_action(log, merged_logs, 'hotkey')
        else:
            # For all other actions, just add them to the merged logs
            merged_logs.append(log)

    return merged_logs

def append_key_to_write_action(log, merged_logs, actual_key):
    if merged_logs and merged_logs[-1]['Action'] == 'write':
        # Append this key to the previous write action
        previous_log = merged_logs[-1]
        # Append the current key or its representation
        previous_log['Key'] += actual_key
        # Update the end timestamp
        previous_log['end_timestamp'] = log['end_timestamp']
    else:
        # Convert this key press-release into a write action
        merged_logs.append({
            'timestamp': log['timestamp'],
            'Action': 'write',
            'Position': None,
            'Key': actual_key,
            'Delta': None,
            'end_timestamp': log['end_timestamp']
        })

def append_new_action(log, merged_logs, action):
    # Create a new action with the specified type
    merged_logs.append({
        'timestamp': log['timestamp'],
        'Action': action,
        'Position': None,
        'Key': log['Key'],
        'Delta': None,
        'end_timestamp': log.get('end_timestamp', log['timestamp'])
    })

def identify_enhanced_hotkey_sequences(parsed_logs):
    merged_logs = []
    # Flags to track the state of modifier keys
    modifier_states = {
        'ctrl': False,
        'shift': False,
        'alt': False
    }
    # Store the timestamps when modifier keys were pressed
    modifier_timestamps = {}

    for log in parsed_logs:
        if log['Key'] is None:
            merged_logs.append(log)
            continue

        key_lower = log['Key'].lower()
        action = log['Action']
        timestamp = log['timestamp']

        # Update modifier states and timestamps
        if action == 'pressed_key':
            if 'ctrl' in key_lower:
                modifier_states['ctrl'] = True
                modifier_timestamps['ctrl'] = timestamp
            elif 'shift' in key_lower:
                modifier_states['shift'] = True
                modifier_timestamps['shift'] = timestamp
            elif 'alt' in key_lower:
                modifier_states['alt'] = True
                modifier_timestamps['alt'] = timestamp

        # Check for modifier release
        if action == 'released_key':
            if 'ctrl' in key_lower:
                modifier_states['ctrl'] = False
            elif 'shift' in key_lower:
                modifier_states['shift'] = False
            elif 'alt' in key_lower:
                modifier_states['alt'] = False
            # Continue to next log without adding a release event yet
            # continue

        # Construct and add hotkey action if applicable
        if action == 'pressed_key' and (modifier_states['ctrl'] or modifier_states['shift'] or modifier_states['alt']):
            # Only consider non-modifier keys for hotkey combinations
            if not any(mod in key_lower for mod in ['ctrl', 'shift', 'alt']):
                hotkey = '+'.join(part for part, pressed in modifier_states.items()
                                  if pressed) + '+' + log['Key']
                merged_logs.append({
                    'timestamp': min(modifier_timestamps.values()),
                    'Action': 'hotkey',
                    'Position': None,
                    'Key': hotkey,
                    'Delta': None,
                    'end_timestamp': timestamp
                })
        else:
            # Add non-hotkey actions directly
            merged_logs.append(log)

        # Reset timestamps if all modifiers are released
        if not any(modifier_states.values()):
            modifier_timestamps.clear()

    return merged_logs

def merge_similar_consecutive_actions_with_delta(parsed_logs):
    merged_logs = []
    previous_log = None

    for log in parsed_logs:
        if log is None:
            continue 
        # Check if the current log is similar to the previous one (excluding timestamp, end_timestamp, and Delta)
        if previous_log and all(log[key] == previous_log[key] for key in log if key not in ['timestamp', 'end_timestamp', 'Delta']):
            # Initialize can_merge as True
            can_merge = True
            # Proceed to check Delta only if both current and previous logs have a non-None Delta
            if previous_log['Delta'] is not None and log['Delta'] is not None:
                # Check if both Deltas have the same sign for each component
                can_merge = all(a * b >= 0 for a,
                                b in zip(previous_log['Delta'], log['Delta']))

            if can_merge:
                # Update end_timestamp to current log's timestamp
                previous_log['end_timestamp'] = log['timestamp']
                # Accumulate delta if present and not None
                if previous_log['Delta'] is not None and log['Delta'] is not None:
                    previous_log['Delta'] = tuple(sum(x) for x in zip(
                        previous_log['Delta'], log['Delta']))
            else:
                # If cannot merge, add previous log to merged logs
                merged_logs.append(previous_log)
                previous_log = log.copy()  # Reset for current log
        else:
            # If current and previous logs are different, add previous to merged logs
            if previous_log:
                merged_logs.append(previous_log)
            previous_log = log.copy()  # Set current log as previous for next iteration

    # Add the last log if it exists
    if previous_log:
        merged_logs.append(previous_log)

    return merged_logs

def translate_hotkey(action_dict):
    """将hotkey操作转换为实际键盘按键，包括数字和符号的转义"""

    # Mapping for control characters (from \x01 to \x1A) to corresponding letters A-Z
    control_key_mapping = {
        '\\x01': 'A', '\\x02': 'B', '\\x03': 'C', '\\x04': 'D', '\\x05': 'E',
        '\\x06': 'F', '\\x07': 'G', '\\x08': 'H', '\\x09': 'I', '\\x0A': 'J',
        '\\x0B': 'K', '\\x0C': 'L', '\\x0D': 'M', '\\x0E': 'N', '\\x0F': 'O',
        '\\x10': 'P', '\\x11': 'Q', '\\x12': 'R', '\\x13': 'S', '\\x14': 'T',
        '\\x15': 'U', '\\x16': 'V', '\\x17': 'W', '\\x18': 'X', '\\x19': 'Y',
        '\\x1A': 'Z'
    }

    # Mapping for numeric key codes, for example, <49> is '1', <189> is '='
    numeric_key_mapping = {
        '<49>': '1', '<50>': '2', '<51>': '3', '<52>': '4', '<53>': '5',
        '<54>': '6', '<55>': '7', '<56>': '8', '<57>': '9', '<48>': '0',
        '<189>': '=',  # '=' (usually shift+equals)
        '<190>': '.',  # '.' (period key)
        '<191>': '/',  # '/' (slash key)
        '<192>': '`',  # '`' (backtick key)
        '<189>': '-',  # '-' (minus key)
        '<187>': '+',  # '+' (plus key, typically shift+equals)
        '<219>': '[',  # '[' (left bracket key)
        '<221>': ']',  # ']' (right bracket key)
        '<222>': "'",  # "'" (apostrophe key)
        '<220>': '\\', # '\\' (backslash key)
        '<13>': 'Enter', # Enter key (commonly <13>)
        '<8>': 'Backspace', # Backspace key (commonly <8>)
    }

    # First, handle the standard mapping of control characters and number symbols
    hotkey_name = action_dict['Key']

    # Replace control key symbols like \x01, \x02, ... with their corresponding letters
    for control_key, letter in control_key_mapping.items():
        hotkey_name = hotkey_name.replace(control_key, letter)

    # Replace numeric key codes like <49>, <50> with corresponding keys
    for numeric_key, symbol in numeric_key_mapping.items():
        hotkey_name = hotkey_name.replace(numeric_key, symbol)

    # Update the Key in the action_dict with the translated hotkey name
    action_dict['Key'] = hotkey_name

    return action_dict

def merge_final_scroll_events(parsed_logs):
    """
    对解析后的日志中 Action 为 "scroll" 的记录进行最后合并：
      - 如果相邻的 scroll 事件（虽然 log 文件中不连续，但逻辑上连续）满足以下条件：
          * 两个事件的位置足够接近（manhattan_distance < 20）
          * 两个事件的 Delta 的 y 分量符号一致（即同向滚动）
        则将它们合并为一条记录：更新 end_timestamp，并累加 Delta 值。
    返回合并后的日志列表。
    """
    merged_logs = []
    previous_log = None

    for log in parsed_logs:
        if log is None:
            continue

        if log.get("Action") == "scroll":
            if previous_log is not None and previous_log.get("Action") == "scroll":
                # 如果两条记录位置接近且 delta 同向，则合并
                if (manhattan_distance(log.get("Position"), previous_log.get("Position")) < 20 and
                        (log.get("Delta")[1] * previous_log.get("Delta")[1] >= 0)):
                    # 更新前一条记录的结束时间与累计 delta
                    previous_log["end_timestamp"] = log.get("timestamp")
                    previous_log["Delta"] = (
                        previous_log["Delta"][0] + log["Delta"][0],
                        previous_log["Delta"][1] + log["Delta"][1]
                    )
                    # 不将当前记录单独加入，而是继续等待合并
                    continue
                else:
                    merged_logs.append(previous_log)
                    previous_log = log.copy()
            else:
                if previous_log:
                    merged_logs.append(previous_log)
                previous_log = log.copy()
        else:
            # 当前记录不是 scroll，则先将待合并的 scroll 记录输出
            if previous_log:
                merged_logs.append(previous_log)
                previous_log = None
            merged_logs.append(log)
    if previous_log:
        merged_logs.append(previous_log)
    return merged_logs

def merge_final_ctrl_scroll_events(parsed_logs):
    """
    对解析后的日志中 Action 为 "hotkey" 且 Key 包含 "ctrl+scroll" 的记录进行最后合并：
      - 如果相邻的 ctrl+scroll 事件（虽然 log 文件中可能不相邻，但逻辑上连续）满足以下条件：
          * 两个事件的位置足够接近（manhattan_distance < 20）
          * 两个事件的 Delta 的 y 分量符号一致（即同向滚动）
        则将它们合并为一条记录：更新 end_timestamp，并累加 Delta 值。
    返回合并后的日志列表。
    """
    merged_logs = []
    previous_log = None

    for log in parsed_logs:
        if log is None:
            continue

        if log.get("Action") == "hotkey" and "ctrl+scroll" in log.get("Key", "").lower():
            if previous_log is not None and previous_log.get("Action") == "hotkey" and "ctrl+scroll" in previous_log.get("Key", "").lower():
                if (manhattan_distance(log.get("Position"), previous_log.get("Position")) < 20 and
                        (log.get("Delta")[1] * previous_log.get("Delta")[1] >= 0)):
                    previous_log["end_timestamp"] = log.get("timestamp")
                    previous_log["Delta"] = (
                        previous_log["Delta"][0] + log["Delta"][0],
                        previous_log["Delta"][1] + log["Delta"][1]
                    )
                    continue
                else:
                    merged_logs.append(previous_log)
                    previous_log = log.copy()
            else:
                if previous_log:
                    merged_logs.append(previous_log)
                previous_log = log.copy()
        else:
            if previous_log:
                merged_logs.append(previous_log)
                previous_log = None
            merged_logs.append(log)
    if previous_log:
        merged_logs.append(previous_log)
    return merged_logs

def handle_shift_hotkey(parsed_logs):
    """
    针对包含 shift 修饰但实际仅用于输入字符的情况进行处理：
      - 如果某条记录 Action 为 "hotkey"，并且 Key 字段格式为 "shift+<char>"（且只有单个字符），
        则将其转换为普通字符输入（write 事件）。
      - 对于字母，转换为大写；对于数字或符号，可以根据需要进行映射（此处示例中直接保持不变）。
      - 如果 hotkey 同时包含其它 modifier（例如 ctrl、alt），则不做转换，保留为热键组合。
    """
    processed_logs = []
    for log in parsed_logs:
        # 仅处理 hotkey 类型的记录
        if log.get("Action") == "hotkey":
            key_val = log.get("Key", "")
            # 检查 hotkey 是否只包含 shift 修饰符，例如 "shift+!" 或 "shift+a"
            # 注意：如果日志中生成的 hotkey 组合里可能有空格或大小写问题，这里统一转为小写比较
            lower_key = key_val.lower()
            # 判断是否只包含 shift 修饰（不包含 ctrl、alt 等）
            if lower_key.startswith("shift+") and ("ctrl" not in lower_key and "alt" not in lower_key):
                candidate = key_val[len("shift+"):]  # 保留原始大小写部分
                # 如果候选部分仅有一个字符，认为是常规字符输入
                if len(candidate) == 1:
                    log["Action"] = "write"
                    # 对字母转换为大写（数字和符号通常已经正确）
                    if candidate.isalpha():
                        log["Key"] = candidate.upper()
                    else:
                        log["Key"] = candidate
        processed_logs.append(log)
    return processed_logs

def merge_write_actions(parsed_logs, time_threshold_ms=1000):
    """
    合并连续的 write 事件：
      1. 先对日志按 timestamp 排序，确保时间顺序正确。
      2. 如果相邻的 write 事件之间的时间间隔小于 time_threshold_ms（毫秒），
         则认为它们是连续输入，将它们合并为一条记录：
            - 将后续 write 记录的 Key 拼接到前一个 write 的 Key 后面
            - 更新前一个 write 的 end_timestamp 为最后一个 write 的结束时间
      3. 非 write 事件保持不变。
      
    参数:
      parsed_logs: 解析后的日志列表
      time_threshold_ms: 合并连续 write 的时间间隔阈值，单位毫秒
      
    返回:
      合并后的日志列表
    """
    def parse_timestamp(ts):
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H-%M-%S-%f")
        except Exception as e:
            return datetime.min

    # 先对日志按 timestamp 排序
    sorted_logs = sorted(parsed_logs, key=lambda log: parse_timestamp(log.get("timestamp", "")))
    
    merged_logs = []
    previous_write = None

    for log in sorted_logs:
        if log.get("Action") == "write":
            if previous_write is None:
                previous_write = log.copy()
            else:
                # 计算前一个 write 的 end_timestamp 与当前 write 的 timestamp 之间的时间差（毫秒）
                prev_end = parse_timestamp(previous_write.get("end_timestamp", previous_write["timestamp"]))
                current_ts = parse_timestamp(log["timestamp"])
                gap_ms = (current_ts - prev_end).total_seconds() * 1000
                if gap_ms <= time_threshold_ms:
                    # 时间间隔足够近，合并 write 操作
                    previous_write["Key"] += log.get("Key", "")
                    previous_write["end_timestamp"] = log.get("end_timestamp", log["timestamp"])
                else:
                    # 间隔太长，则认为是新的 write 操作
                    merged_logs.append(previous_write)
                    previous_write = log.copy()
        else:
            if previous_write is not None:
                merged_logs.append(previous_write)
                previous_write = None
            merged_logs.append(log)
    if previous_write is not None:
        merged_logs.append(previous_write)
    
    return merged_logs
