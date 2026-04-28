"""Model-variant forward functions and fitters.

Each module here registers its variant's forward function with the
model_layer dispatch registry on import. Loading this package wires
all currently-implemented variants. Future variants drop a new module
in this package and register themselves the same way.
"""

from behavtaskatlas.model_fits import logistic as _logistic  # noqa: F401
from behavtaskatlas.model_fits import sdt as _sdt  # noqa: F401
