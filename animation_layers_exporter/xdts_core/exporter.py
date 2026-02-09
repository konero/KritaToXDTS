"""XDTS Export Engine

Main export logic for converting Krita animations to XDTS format with image frames.
"""

import os

from ..config import DEFAULT_PNG_COMPRESSION, SYMBOL_NULL_CELL
from .utils import mkdir, sanitize_filename, int_to_str, compute_content_hash, make_unique_name
from .document import get_document_info
from .layer import get_animated_layers, get_static_layers, get_layer_keyframes, count_total_keyframes, is_stop_frame
from .frame_export import FrameExporter
from .xdts_file import (
    create_xdts_document,
    add_track,
    add_frame_to_track,
    add_track_terminator,
    write_xdts_file,
)


class ExportOptions:
    """Configuration options for XDTS export."""
    
    # File format constants
    FORMAT_SEQ_ONLY = 0       # 0001.ext
    FORMAT_LAYER_SEQ = 1      # LayerName_0001.ext
    
    def __init__(self):
        self.include_invisible = False
        self.include_reference = False
        self.include_static = False
        self.flatten_groups = False
        self.png_compression = DEFAULT_PNG_COMPRESSION
        self.use_full_clip_range = True
        
        # File naming options
        self.file_format = self.FORMAT_LAYER_SEQ
        self.file_prefix = ""
        self.file_suffix = ""
        self.file_separator = "_"
        self.export_name = ""
        self.image_format = "png"
        
    @classmethod
    def from_dict(cls, data: dict):
        """Create ExportOptions from a dictionary."""
        opts = cls()
        opts.include_invisible = data.get('include_invisible', False)
        opts.include_reference = data.get('include_reference', False)
        opts.include_static = data.get('include_static', False)
        opts.flatten_groups = data.get('flatten_groups', False)
        opts.png_compression = data.get('png_compression', DEFAULT_PNG_COMPRESSION)
        opts.use_full_clip_range = data.get('use_full_clip_range', True)
        opts.file_format = data.get('file_format', cls.FORMAT_LAYER_SEQ)
        opts.file_prefix = data.get('file_prefix', "")
        opts.file_suffix = data.get('file_suffix', "")
        opts.file_separator = data.get('file_separator', "_")
        opts.export_name = data.get('export_name', "")
        opts.image_format = data.get('image_format', "png")
        return opts


class ExportResult:
    """Result of an export operation."""
    
    def __init__(self):
        self.success = False
        self.output_path = ""
        self.track_count = 0
        self.frame_count = 0
        self.unique_frames_exported = 0
        self.error_message = ""
        
    def __str__(self):
        if self.success:
            return (f"Export complete: {self.track_count} tracks, "
                    f"{self.unique_frames_exported} unique frames")
        return f"Export failed: {self.error_message}"


class XDTSExportEngine:
    """Core export engine for XDTS animation export.
    
    Converts Krita animation documents to XDTS format with image sequences.
    """
    
    def __init__(self, document, export_path: str, options=None):
        """Initialize the export engine.
        
        Args:
            document: The Krita document to export.
            export_path: Directory where exports will be saved.
            options: Export configuration options (ExportOptions or None).
        """
        self.document = document
        self.export_path = export_path
        self.options = options if options is not None else ExportOptions()
        
        # Callbacks for progress reporting
        self.on_progress = None  # Callable: (current, total, message) -> None
        self.on_cancelled = None  # Callable: () -> bool
        
        # Export state
        self._result = ExportResult()
        
    def export(self) -> ExportResult:
        """Execute the export operation.
        
        Returns:
            ExportResult with details of the operation.
        """
        try:
            self._run_export()
        except Exception as e:
            self._result.success = False
            self._result.error_message = str(e)
        
        return self._result
    
    def _report_progress(self, current: int, total: int, message: str):
        """Report progress if callback is set."""
        if self.on_progress:
            self.on_progress(current, total, message)
    
    def _is_cancelled(self) -> bool:
        """Check if export was cancelled."""
        return self.on_cancelled and self.on_cancelled()
    
    def _run_export(self):
        """Internal export implementation."""
        # Gather document info
        doc_info = get_document_info(self.document)
        
        # Get exportable animated layers (includes group layers if flatten_groups is enabled)
        animated_layers = get_animated_layers(
            self.document,
            self.options.include_invisible,
            self.options.include_reference,
            self.options.flatten_groups
        )
        
        # Get static layers if requested
        static_layers = []
        if self.options.include_static:
            static_layers = get_static_layers(
                self.document,
                self.options.include_invisible,
                self.options.include_reference
            )
        
        if not animated_layers and not static_layers:
            self._result.error_message = "No exportable layers found"
            return
        
        # Determine frame range
        if self.options.use_full_clip_range:
            start_frame = doc_info['start_frame']
            end_frame = doc_info['end_frame']
        else:
            start_frame = self.document.playBackStartTime()
            end_frame = self.document.playBackEndTime()
        
        duration = end_frame - start_frame + 1
        
        # Count total work for progress reporting (animated keyframes + static layers)
        total_keyframes = count_total_keyframes(animated_layers, start_frame, end_frame)
        total_work = total_keyframes + len(static_layers)
        
        # Create XDTS document structure
        xdts_doc = create_xdts_document(duration)
        
        # Initialize the frame exporter (handles temp document creation)
        frame_exporter = FrameExporter(self.document)
        
        # Process each animated layer
        processed = 0
        total_unique = 0
        used_layer_names = set()  # Track used names to handle duplicates
        
        for track_no, layer in enumerate(animated_layers):
            base_name = sanitize_filename(layer.name())
            layer_name = make_unique_name(base_name, used_layer_names)
            layer_folder = os.path.join(self.export_path, layer_name)
            mkdir(layer_folder)
            
            # Create track in XDTS document
            track = add_track(xdts_doc, layer_name, track_no)
            
            # For deduplication: map content hash -> cell label
            hash_to_label = {}
            cell_count = 0
            
            # Get keyframes for this layer
            keyframes = get_layer_keyframes(layer, start_frame, end_frame)
            
            # Track if we've hit a stop frame (blank keyframe) - used for track termination
            last_was_stop_frame = False
            
            for frame in keyframes:
                # Check for cancellation
                if self._is_cancelled():
                    self._result.error_message = "Export cancelled by user"
                    return
                
                # Report progress
                processed += 1
                self._report_progress(
                    processed, 
                    total_work,
                    f"Exporting {layer_name} - frame {frame}..."
                )
                
                relative_frame = frame - start_frame
                
                # Set document to this frame for stop frame detection
                self.document.setCurrentTime(frame)
                self.document.waitForDone()
                
                # Check for stop frame (blank keyframe)
                # When a blank frame is detected, emit null cell to end the hold
                if is_stop_frame(layer):
                    add_frame_to_track(track, relative_frame, SYMBOL_NULL_CELL)
                    last_was_stop_frame = True
                    continue  # Continue processing - there may be more content after
                
                last_was_stop_frame = False
                
                # Determine cell label (with deduplication)
                cell_label = self._process_frame(
                    frame_exporter, layer, frame, 
                    layer_name, layer_folder,
                    doc_info, hash_to_label
                )
                
                if cell_label is None:
                    # Export failed
                    self._result.error_message = f"Failed to export frame {frame} of {layer_name}"
                    return
                
                # Track unique exports
                cell_num = int(cell_label) if cell_label.isdigit() else 0
                if cell_num > cell_count:
                    cell_count = cell_num
                    total_unique += 1
                
                # Add frame reference to XDTS track
                add_frame_to_track(track, relative_frame, cell_label)
            
            # Terminate track with null cell (only if we didn't end on a stop frame)
            if not last_was_stop_frame:
                add_track_terminator(track, duration)
            
            self._result.frame_count += len(keyframes)
        
        # Export static layers (as single images, no folders)
        static_exported = 0
        for layer in static_layers:
            # Check for cancellation
            if self._is_cancelled():
                self._result.error_message = "Export cancelled by user"
                return
            
            base_name = sanitize_filename(layer.name())
            layer_name = make_unique_name(base_name, used_layer_names)
            
            # Report progress
            processed += 1
            self._report_progress(
                processed,
                total_work,
                f"Exporting static layer {layer_name}..."
            )
            
            # Export as single image directly in export folder (no subfolder)
            filename = f"{layer_name}.{self.options.image_format}"
            filepath = os.path.join(self.export_path, filename)
            
            # Use first frame for static layers
            success = frame_exporter.export_frame(layer, start_frame, filepath)
            
            if success:
                static_exported += 1
            else:
                # Non-fatal - continue with other layers
                self._report_progress(
                    processed,
                    total_work,
                    f"Warning: Failed to export {layer_name}"
                )
        
        # Write the XDTS file using export name
        xdts_filename = sanitize_filename(self.options.export_name) if self.options.export_name else "export"
        xdts_path = os.path.join(self.export_path, f"{xdts_filename}.xdts")
        write_xdts_file(xdts_doc, xdts_path)
        
        # Update result
        self._result.success = True
        self._result.output_path = xdts_path
        self._result.track_count = len(animated_layers)
        self._result.unique_frames_exported = total_unique + static_exported
    
    def _build_filename(self, layer_name: str, cell_number: int) -> str:
        """Build a filename based on the configured naming options.
        
        Args:
            layer_name: Sanitized layer name.
            cell_number: The cell/sequence number.
            
        Returns:
            Filename string (without path).
        """
        sep = self.options.file_separator
        prefix = self.options.file_prefix
        suffix = self.options.file_suffix
        seq = int_to_str(cell_number)
        
        parts = []
        
        # Add prefix if specified
        if prefix:
            parts.append(prefix)
        
        # Add layer name based on format
        if self.options.file_format == ExportOptions.FORMAT_LAYER_SEQ:
            parts.append(layer_name)
        
        # Add suffix if specified
        if suffix:
            parts.append(suffix)
        
        # Add sequence number
        parts.append(seq)
        
        return sep.join(parts) + f".{self.options.image_format}"
    
    def _process_frame(self, frame_exporter, layer, frame: int,
                       layer_name: str, layer_folder: str,
                       doc_info: dict, hash_to_label: dict) -> str:
        """Process and potentially export a single frame.
        
        Handles deduplication by checking content hashes before export.
        
        Args:
            frame_exporter: FrameExporter instance.
            layer: The layer being exported.
            frame: Frame number.
            layer_name: Sanitized layer name for filenames.
            layer_folder: Output folder for this layer.
            doc_info: Document information dict.
            hash_to_label: Hash-to-label map for deduplication.
            
        Returns:
            Cell label string, or None if export failed.
        """
        # Set document to the target frame for projection data
        self.document.setCurrentTime(frame)
        self.document.waitForDone()
        
        # Check for duplicate content using pixel hash (always deduplicate)
        # Use projectionPixelData which works for both paint layers and groups
        pixel_data = layer.projectionPixelData(
            0, 0, 
            doc_info['width'], doc_info['height']
        )
        content_hash = compute_content_hash(pixel_data)
        
        # Return existing label if we've seen this content before
        if content_hash in hash_to_label:
            return hash_to_label[content_hash]
        
        # New unique content - assign next cell number
        cell_number = len(hash_to_label) + 1
        cell_label = str(cell_number)
        
        # Record hash for future deduplication
        hash_to_label[content_hash] = cell_label
        
        # Build output filename using configured format
        filename = self._build_filename(layer_name, cell_number)
        filepath = os.path.join(layer_folder, filename)
        
        # Export the frame
        success = frame_exporter.export_frame(layer, frame, filepath)
        
        return cell_label if success else None
