from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Type, TypeVar, Dict, Callable

TClouds = TypeVar("TClouds", bound="Clouds")

"""
Clouds Module

Defines the Clouds class, which represents cloud and haze information.

Author: Z. Gerber
Date: August, 2024
"""


@dataclass
class Clouds:
    """
    Represents cloud and haze information.

    Attributes:
        north (int): Cloud coverage in the North.
        east (int): Cloud coverage in the East.
        south (int): Cloud coverage in the South.
        west (int): Cloud coverage in the West.
        overhead (int): Overhead cloud coverage.
        thickness (int): Cloud thickness (0 = stars visible, 1 = stars not visible).
        haze (int): Haze (0 = no haze, 1 = haze).
    """
    north: int
    east: int
    south: int
    west: int
    overhead: int
    thickness: int
    haze: int

    def to_list(self, include_haze: bool = True) -> List[int]:
        """Converts cloud attributes to a list."""
        haze = [self.haze] if include_haze else []
        return [self.north, self.east, self.south, self.west, self.overhead, self.thickness] + haze

    def to_string(self) -> str:
        """Converts the Clouds instance to a string representation."""
        return "".join(map(str, self.to_list()))

    def calculate_sum(self, sum_type: str = "total") -> int:
        """
        Sums cloud attributes based on the specified type.

        Args:
            sum_type (str): Type of sum ('total', 'horizon', 'overhead').

        Returns:
            int: Sum of specified cloud attributes.
        """
        sums = {
            "total": sum(self.to_list()),
            "horizon": self.north + self.east + self.south + self.west,
            "overhead": self.overhead + self.thickness
        }
        return sums.get(sum_type, 0)

    @classmethod
    def perfect_conditions(cls) -> "Clouds":
        """Returns Clouds instance with perfect weather conditions."""
        return cls(0, 0, 0, 0, 0, 0, 0)

    @classmethod
    def from_string(cls, weather_string: str) -> "Clouds":
        """Creates Clouds instance from a string representation."""
        return cls(*map(int, weather_string))

    @classmethod
    def compare_clouds(cls, first_clouds: "Clouds", second_clouds: "Clouds", weight_first: float = 1,
                       weight_second: float = 1, algorithm: str = "match") -> "Clouds":
        """
        Compares two Clouds instances using a specified algorithm.

        Args:
            first_clouds (Clouds): First Clouds instance.
            second_clouds (Clouds): Second Clouds instance.
            weight_first (float): Weight for the first instance.
            weight_second (float): Weight for the second instance.
            algorithm (str): Comparison algorithm ('match', 'worse', 'average', 'latest', 'twavg').

        Returns:
            Clouds: Resultant Clouds instance.
        """

        def average(a, b):
            return int(Decimal(0.5 * (a + b)).to_integral_value(rounding=ROUND_HALF_UP))

        def time_weighted_average(a, b):
            return int(
                Decimal((a * weight_second + b * weight_first) / (weight_first + weight_second)).to_integral_value(
                    rounding=ROUND_HALF_UP))

        comparison_strategies = {
            "match": lambda first, second: second if second == first else 9,
            "worse": max,
            "average": average,
            "latest": lambda first, second: second,
            "twavg": time_weighted_average
        }

        comparison_function = comparison_strategies.get(algorithm)
        if not comparison_function:
            raise NotImplementedError(f"Algorithm '{algorithm}' is not implemented!")

        return cls(*(comparison_function(getattr(first_clouds, attr), getattr(second_clouds, attr)) for attr in
                     cls.__annotations__))
