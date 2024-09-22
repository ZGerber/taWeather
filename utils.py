"""
Utility Functions Module

Provides utility functions for time conversion, XML parsing, and other helper functions.

Author: Z. Gerber
Date: August 2024
"""
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Union, Dict, Tuple


def load_xml_file(file_path: Path) -> ET.Element:
    """
    Load an XML file and return the root element of the XML tree.

    Args:
        file_path (Path): Path to the XML file.

    Returns:
        ET.Element: Root element of the XML tree.
    """
    tree = ET.parse(file_path)
    return tree.getroot()


def convert_to_seconds(time_list: Union[List[datetime], datetime]) -> Union[List[int], int]:
    """
    Convert a datetime object or list of datetime objects to seconds since midnight.

    Args:
        time_list (Union[List[datetime], datetime]): List of datetime objects or a single datetime object.

    Returns:
        Union[List[int], int]: List of seconds since midnight if input is a list; otherwise, a single integer.
    """
    if isinstance(time_list, list):
        return [int(timedelta(hours=t.hour, minutes=t.minute, seconds=t.second).total_seconds()) for t in time_list]
    elif isinstance(time_list, datetime):
        return int(timedelta(hours=time_list.hour, minutes=time_list.minute, seconds=time_list.second).total_seconds())
    else:
        raise TypeError("Input must be a datetime object or a list of datetime objects.")


def parse_time_string(time_str: str, format_str: str = "%H:%M:%S") -> datetime:
    """
    Convert a string representation of time to a datetime object.

    Args:
        time_str (str): Time in string format.
        format_str (str): Format of the time string. Defaults to "%H:%M:%S".

    Returns:
        datetime: Corresponding datetime object.
    """
    return datetime.strptime(time_str, format_str)


def filter_corrections(weather_times: List[int], time_window: int = 600) -> List[int]:
    """
    Filter out weather codes entered close to one another, assuming the first entry is a correction.

    Args:
        weather_times (List[int]): List of weather times in seconds since midnight.
        time_window (int): Time window in seconds to consider for corrections. Defaults to 10 minutes.

    Returns:
        List[int]: Filtered list of weather times.
    """
    filtered_times = []
    prev_time = None
    for current_time in weather_times:
        if prev_time is None or (current_time - prev_time) >= time_window:
            filtered_times.append(current_time)
        prev_time = current_time
    return filtered_times
