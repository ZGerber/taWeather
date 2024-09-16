from dataclasses import dataclass, field
from typing import Optional
from clouds import Clouds


@dataclass
class DataPart:
    """
    Represents a segment of data within a specified time range, including associated weather codes.

    Attributes:
        part_number (int): Identifier for the data part.
        start_time (int): Start time of the data part in seconds since midnight.
        stop_time (int): Stop time of the data part in seconds since midnight.
        mid_time (int): Midpoint time of the data part in seconds since midnight.
        max_time (int): Maximum considered time of the data part in seconds since midnight.
        weat_code (Optional[Clouds]): Associated weather code for the data part.
        weat_time (Optional[int]): Time of the associated weather code in seconds since midnight.
        source (Optional[str]): Source identifier for the weather data (e.g., "local" or "remote").
    """
    part_number: int
    start_time: int
    stop_time: int
    mid_time: int
    max_time: int
    weat_code: Optional[Clouds] = field(default=None)
    weat_time: Optional[int] = field(default=None)
    source: Optional[str] = field(default=None)

    def update_weat_code(self, weat_code: Clouds, weat_time: int, source: str) -> None:
        """
        Updates the weather code, time, and source for the data part.

        Args:
            weat_code (Clouds): The weather code to set.
            weat_time (int): The time associated with the weather code in seconds since midnight.
            source (str): The source of the weather code.
        """
        self.weat_code = weat_code
        self.weat_time = weat_time
        self.source = source

    @property
    def part_duration(self):
        """ Determine the duration of the data part in seconds"""
        return self.stop_time - self.start_time
