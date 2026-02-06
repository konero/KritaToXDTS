# Krita To XDTS Exporter
Export animated paint layers as image sequences with timing data saved in the Toei Digital Exposure Sheet format (.XDTS), compatible with other apps like OpenToonz, Tahoma2D, Clip Studio Paint and more.

## Overview
**Key Features:**
- Export Krita animation layers as numbered image sequences
- Generate industry-standard .XDTS exposure sheet files
- Support for grouped layers, static layers, reference layers
- Compatible with Clip Studio Paint, OpenToonz, Tahoma2D, and other XDTS-compatible apps

## Use Cases
- **Traditional animation workflow**: Export rough animation from Krita for cleanup in Clip Studio Paint, or to OpenToonz/Tahoma2D for celpaint and compositing

## Installation
1. Download the plugin by clicking the green `Code` button at the top and save as `.ZIP`
2. In Krita, navigate to the menu: `Tools/Scripts/Install Python Plugin from File...`
3. Select the downloaded .ZIP file
4. Restart Krita

## Usage
1. Go to Tools > Scripts > `Export Animation Layers (XDTS)...`
2. Select an export directory and configure options
3. Click export

## Export Options

### Flatten animated groups
> Group layers containing animated children are exported as single flattened images. This is useful when you have separate layers for lines and paint, or multiple layers for different colored lines, inside a group that should be combined in the final export. When disabled, only individual paint layers are exported.

### Include invisible layers
> Export layers that are currently hidden in the layer panel.

### Include reference layers (grey-labeled)
> Export layers marked with a grey color label. By default, grey-labeled layers are treated as animation reference guides and excluded from export.

### Include non-animated layers
> Export static layers (without animation keyframes) as single images. Useful for backgrounds, layouts, peg bars, or safety margin frames. Static layers are exported directly into the export folder without subfolders and not included in the .XDTS exposure sheet file.

### Use full clip range
> Export the entire animation timeline. When disabled, only the selected playback range (in/out points) is exported.

## Output Structure
```
chosen_directory/
└── DocumentName/              # Export folder (named after your document)
    ├── DocumentName.xdts      # XDTS timing sheet
    ├── BG1.png                # Static layers (single images, no folder)
    ├── Layout.png             # Another static layer
    ├── A/                     # Folder for each animated layer/group
    │   ├── A_0001.png
    │   ├── A_0002.png
    │   └── ...
    ├── B/
    │   ├── B_0001.png
    │   └── ...
    └── ...
```

## Importing into Other Software
### Clip Studio Paint
1. Go to `File > Import > Exposure sheet`
2. Select the .XDTS file
3. The timing will be applied to the timeline
4. Import the image sequences

### OpenToonz / Tahoma2D
1. Go to `File > Load Scene`
3. Select the .XDTS file
4. Confirm the asset folder paths (should be auto-filled)
5. All image sequences and timing will be applied to the scene

## Troubleshooting

### "No animated layers found" error
This error appears when no exportable animation layers are detected. Check that:

- Your document has paint layers (or groups with paint layers inside)
- The layers have animation keyframes on the timeline
- The layers are visible, or enable "Include invisible layers"
- The layers don't have a grey color label, or enable "Include reference layers"

## Requirements
- Krita 5.0 or later

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request.

# License
This plugin is released under the GPL-3.0 license. See LICENSE file for details.

## Related Projects

- [Krita](https://krita.org/) - Free and open-source painting program
- [Krita to OpenToonz Exporter](https://github.com/konero/KritaToOpenToonz/) - Krita plugin
- [OpenToonz](https://opentoonz.github.io/e/) - Open-source animation production software
- [Tahoma2D](https://tahoma2d.org/) - Community fork of OpenToonz
