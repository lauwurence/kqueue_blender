################################################################################
## Filter Frames

from re import compile, VERBOSE
from numpy import arange, around, isclose

rx_filter = compile(r"""
[\^\!]? \s*?                                                                    # Exclude option
[-+]?                                                                           # Negative or positive number
(?:
    # Range & increment 1-2x2, 0.0-0.1x.02
    (?: \d* \.? \d+ \s? \- \s? \d* \.? \d+ \s? [x%] \s? [-+]? \d* \.? \d+ )
    |
    # Range 1-2, 0.0-0.1 etc
    (?: \d* \.? \d+ \s? \- \s? [-+]? \d* \.? \d+ )
    |
    # .1 .12 .123 etc 9.1 etc 98.1 etc
    (?: \d* \. \d+ )
    |
    # 1. 12. 123. etc 1 12 123 etc
    (?: \d+ \.? )
)
""", VERBOSE)

rx_group = compile(r"""
([-+]? \d*? \.? [0-9]+ \b)                                                      # Start frame
(\s*? \- \s*?)                                                                  # Minus
([-+]? \d* \.? [0-9]+)                                                          # End frame
( (\s*? [x%] \s*? )( [-+]? \d* \.? [0-9]+ \b ) )?                               # Increment
""", VERBOSE)

rx_exclude = compile(r"""
[\^\!] \s*?                                                                     # Exclude option
([-+]? \d* \.? \d+)$                                                            # Int or Float
""", VERBOSE)


def filter_frames(frame_input, increment=1, filter_individual=False):
    """
    Filter frame input & convert it to a set of frames.
    """
    def float_filter(st):
        try:
            return float(st)
        except ValueError:
            return None

    def int_filter(flt):
        try:
            return int(flt) if flt.is_integer() else None
        except ValueError:
            return None


    input_filtered = rx_filter.findall(frame_input)
    if not input_filtered: return None

    """
    Option to add a ^ or ! at the beginning to exclude frames.
    """
    if not filter_individual:
        first_exclude_item = next((i for i, v in enumerate(input_filtered) if "^" in v or "!" in v), None)
        if first_exclude_item:
            input_filtered = input_filtered[:first_exclude_item] + \
                             [elem if elem.startswith(("^", "!")) else "^" + elem.lstrip(' ') \
                              for elem in input_filtered[first_exclude_item:]]

    """
    Find single values as well as all ranges & compile frame list.
    """
    frame_list, exclude_list, conform_list  = [], [], []

    conform_flag = False
    for item in input_filtered:
        frame = float_filter(item)

        if frame is not None: # Single floats
            frame_list.append(frame)
            if conform_flag: conform_list.append(frame)

        else:  # Ranges & items to exclude
            exclude_item = rx_exclude.search(item)
            range_item = rx_group.search(item)

            if exclude_item:  # Single exclude items like ^-3 or ^10
                exclude_list.append(float_filter(exclude_item.group(1)))
                if filter_individual: conform_flag = True

            elif range_item:  # Ranges like 1-10, 20-10, 1-3x0.1, ^2-7 or ^-3--1
                start = min(float_filter(range_item.group(1)), float_filter(range_item.group(3)))
                end = max(float_filter(range_item.group(1)), float_filter(range_item.group(3)))
                step = increment if not range_item.group(4) else float_filter(range_item.group(6))

                if start < end:  # Build the range & add all items to list
                    frame_range = around(arange(start, end, step), decimals=5).tolist()
                    if item.startswith(("^", "!")):
                        if filter_individual: conform_flag = True
                        exclude_list.extend(frame_range)
                        if isclose(step, (end - frame_range[-1])):
                            exclude_list.append(end)
                    else:
                        frame_list.extend(frame_range)
                        if isclose(step, (end - frame_range[-1])):
                            frame_list.append(end)

                        if conform_flag:
                            conform_list.extend(frame_range)
                            if isclose(step, (end - frame_range[-1])):
                                conform_list.append(end)

                elif start == end:  # Not a range, add start frame
                    if not item.startswith(("^", "!")):
                        frame_list.append(start)
                    else:
                        exclude_list.append(start)

    if filter_individual:
        exclude_list = sorted(set(exclude_list).difference(conform_list))
    float_frames = sorted(set(frame_list).difference(exclude_list))

    """
    Return integers whenever possible.
    """
    int_frames = [ int_filter(frame) for frame in float_frames ]
    return float_frames if None in int_frames else int_frames