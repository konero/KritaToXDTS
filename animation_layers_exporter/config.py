"""Animation Layers Exporter Configuration

Version and constants for the Animation Layers Exporter plugin.
"""

VERSION = "2.0.1"
PLUGIN_ID = "animation_layers_exporter"
PLUGIN_NAME = "Export Animation Layers (XDTS)"

# XDTS format version
XDTS_VERSION = 5

# Default export settings
DEFAULT_PNG_COMPRESSION = 6

# Special markers
SYMBOL_NULL_CELL = "SYMBOL_NULL_CELL"
LIGHT_TABLE_PREFIX = "LT_"
LIGHT_TABLE_NAME = "Light Table"

# Reference layer color label (grey = 8)
# Color labels: 0=none, 1=blue, 2=green, 3=yellow, 4=orange, 5=brown, 6=red, 7=purple, 8=grey
REFERENCE_LAYER_COLOR = 8

# Stop Frame Detection (Workaround)
# Krita doesn't yet support native "stop frames" to end holds on the timeline.
# When enabled, blank (fully transparent) keyframes are treated as stop frames,
# causing the layer to show nothing from that point onward in the XDTS export.
# Set to False when Krita adds native stop frame support.
ENABLE_STOP_FRAME_DETECTION = True

# Supported layer types for animation export
ANIMATED_LAYER_TYPES = ["paintlayer"]
