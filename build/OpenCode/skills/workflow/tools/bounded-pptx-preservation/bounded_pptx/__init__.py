"""SPDX-License-Identifier: MIT

Bounded preservation of original chart dependencies after Artifact Tool export.
No functions in this package author slide text or create workbook data.
"""

from .restore import restore_dependencies

__all__ = ["restore_dependencies"]
