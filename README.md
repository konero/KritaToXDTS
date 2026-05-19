# Krita To XDTS Exporter
Export animated paint layers from Krita as image sequences with timing data saved in the Toei Digital Exposure Sheet format (.XDTS), compatible with other apps like OpenToonz, Tahoma2D, Clip Studio Paint.

**Features:**
- Export animation layers as numbered image sequences (A_####.png)
- Generate industry-standard .XDTS exposure sheet files used in the anime industry to easily import your work into other apps
- Support for grouped layers, static layers and *reference layers

## Installation
1. Download the plugin by clicking the green Code button at the top and save as .ZIP
2. Inside Krita, navigate to the menu: **Tools/Scripts/Install Python Plugin from File...**
3. Select the downloaded .ZIP file and choose to activate the plugin and restart Krita

## Usage
1. Go to Tools > Scripts > **Export Animation Layers (XDTS)...**
2. Select an export directory and configure your options and click the Export button

## Export Options

### Flatten animated groups
> Group layers containing animated children are exported as single flattened images. This is designed due to common convention but it's worth noting there may be drawbacks. This mode is most useful when you have separate layers for lines and paint (or multiple layers for different colored separation lines) inside a group that should be combined in the final export as a single animation level. When disabled, only individual paint layers are exported. See below for typical output structure.

### Include invisible layers
> Export layers that are currently hidden in the layer panel.

### Include reference layers (grey-labeled layers)
> Export layers marked with a grey color label. By default, grey-labeled layers are treated as animation reference guides and excluded from export. Use this for example when you sometimes don't want to export color separation line layers.

### Include non-animated layers
> Export static layers (without animation keyframes) as single images. Useful for backgrounds, layouts, peg bars, or safety margin frames. Static layers are exported directly into the export folder without subfolders and not included in the .XDTS exposure sheet file. You'll need to import them manually into other apps if needed.

### Use full clip range
> Export the entire animation timeline. When disabled, only the selected playback range (in/out points) are exported.

## Output Structure
```
> DocumentName/              # Export folder (named after your document)
--> DocumentName.xdts        # XDTS timesheet file
----> BG1.png                # Static layers (single images, no folder)
----> Layout.png             # Another static layer
----> A/                     # Folder for each animated layer/group
------> A_0001.png
------> A_0002.png
----> B/
------> B_0001.png
etc...
```

## Importing into Other Software
### Clip Studio Paint
1. Go to **File > Import > Exposure sheet** and select the .XDTS timesheet file (the timing will be applied to the timeline)
2. Manually import your image sequences (either drag and drop, or from the File menu)

### OpenToonz / Tahoma2D
1. Go to **File > Load Scene** and select the .XDTS timesheet file
2. Confirm the asset folder paths (should be autofilled), if not you need to manually point each track to the subfolder containing each image sequence

### After Effects
1. Download this script: [xsImport by digits58](https://github.com/digits58/xsImport)
2. and follow the instructions in the readme

## Troubleshooting
### "No animated layers found"
This error appears when no exportable animation layers are detected, you can check that:
- At least one layer has animation keyframes on the timeline
- The animated layers are visible (or enable **Include invisible layers**)
- The layers don't have a grey color label (or enable **Include reference layers**

## Contributing
Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request.

# License
This plugin is released under the GPL-3.0 license. See LICENSE file for details.

## Related Projects
- [Krita](https://krita.org/)
- [Krita to OpenToonz Exporter](https://github.com/konero/KritaToOpenToonz/)
- [OpenToonz](https://opentoonz.github.io/e/)
- [Tahoma2D](https://tahoma2d.org/)
