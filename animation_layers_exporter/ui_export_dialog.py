"""Export Animation Layers Dialog

Modal dialog for exporting animation layers to XDTS format.
"""

import os
import krita

from .qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QProgressDialog, QMessageBox,
    QFileDialog, QCheckBox, QSpinBox, QGroupBox, QLineEdit,
    QApplication, get_window_modality, QUrl, QDesktopServices,
    QDialog, QDialogButtonBox, QComboBox, QSettings, QStandardPaths
)
from .config import VERSION, PLUGIN_NAME, DEFAULT_PNG_COMPRESSION, PLUGIN_ID
from .xdts_core import XDTSExportEngine
from .xdts_core.exporter import ExportOptions
from .xdts_core.utils import sanitize_filename


# File naming format options
FILE_FORMAT_SEQ_ONLY = 0       # 0001 (extension follows chosen image format)
FILE_FORMAT_LAYER_SEQ = 1      # LayerName_0001 (extension follows chosen image format)

# Settings keys
SETTINGS_EXPORT_PATH = "export_path"


def get_default_export_path() -> str:
    """Get the default export path based on the operating system.
    
    Returns the user's Documents folder on all platforms.
    
    Returns:
        Path to the default export directory.
    """
    # QStandardPaths.StandardLocation.DocumentsLocation works on all platforms:
    # - Windows: C:/Users/<USER>/Documents
    # - macOS: /Users/<USER>/Documents  
    # - Linux: /home/<USER>/Documents (or ~/Documents)
    docs_path = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    
    if docs_path and os.path.isdir(docs_path):
        return docs_path
    
    # Fallback to home directory if Documents doesn't exist
    return os.path.expanduser("~")


def get_document_name(document) -> str:
    """Get a sanitized name for the document.
    
    Uses the document filename if available, otherwise returns a default.
    
    Args:
        document: The Krita document.
        
    Returns:
        Sanitized document name suitable for folder/file naming.
    """
    if document is None:
        return "Untitled_Animation"
    
    # Try to get filename
    doc_name = document.name()
    if doc_name:
        # Remove file extension if present
        if '.' in doc_name:
            doc_name = os.path.splitext(doc_name)[0]
        return sanitize_filename(doc_name)
    
    return "Untitled_Animation"


class XDTSExportDialog(QDialog):
    """Modal dialog for exporting animations to XDTS format.
    
    Provides options for file naming, layer filtering,
    compression settings, and frame range selection.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Export Animation Layers (XDTS) - v{VERSION}")
        self.setMinimumWidth(480)
        
        self._document = krita.Krita.instance().activeDocument()
        self._settings = QSettings("krita", PLUGIN_ID)
        
        # Load saved export path or use default
        self._export_path = self._settings.value(
            SETTINGS_EXPORT_PATH, 
            get_default_export_path()
        )
        
        self._setup_ui()
        self._connect_signals()
        self._update_folder_name_default()
        self._load_initial_path()
    
    def _setup_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Header description
        header_label = QLabel(
            "<b>Export Animation Layers (XDTS)</b><br>"
            "Exports animated layers and groups as image sequences with timing " \
            "data saved in the Toei Digital Exposure Sheet (.xdts) format."
        )
        header_label.setWordWrap(True)
        layout.addWidget(header_label)
        
        # === Output Location Group ===
        path_group = QGroupBox("Output Location")
        path_layout = QVBoxLayout()
        path_layout.setContentsMargins(8, 8, 8, 8)
        path_layout.setSpacing(6)
        
        # Directory selection row
        dir_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select export directory...")
        self._path_edit.setReadOnly(True)
        dir_row.addWidget(self._path_edit)
        
        self._browse_button = QPushButton("Browse...")
        dir_row.addWidget(self._browse_button)
        path_layout.addLayout(dir_row)
        
        # Export folder name
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Export folder name:"))
        self._folder_name_edit = QLineEdit()
        self._folder_name_edit.setToolTip(
            "Name of the subfolder to create for this export.\n"
            "The XDTS file and layer folders will be created inside."
        )
        folder_row.addWidget(self._folder_name_edit)
        path_layout.addLayout(folder_row)
        
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # === File Naming Group ===
        naming_group = QGroupBox("File Naming")
        naming_layout = QFormLayout()
        naming_layout.setContentsMargins(8, 8, 8, 8)
        
        # Format dropdown
        self._format_combo = QComboBox()
        self._format_combo.addItem("Sequence number only (0001.ext)", FILE_FORMAT_SEQ_ONLY)
        self._format_combo.addItem("Layer name + sequence (Layer_0001.ext)", FILE_FORMAT_LAYER_SEQ)
        self._format_combo.setCurrentIndex(FILE_FORMAT_LAYER_SEQ)
        self._format_combo.setToolTip("Choose how exported frame files are named.")
        naming_layout.addRow("Format:", self._format_combo)
        
        # Prefix
        self._prefix_edit = QLineEdit()
        self._prefix_edit.setPlaceholderText("Optional")
        self._prefix_edit.setToolTip("Text to add before the layer name/sequence number.")
        naming_layout.addRow("Prefix:", self._prefix_edit)
        
        # Suffix
        self._suffix_edit = QLineEdit()
        self._suffix_edit.setPlaceholderText("Optional")
        self._suffix_edit.setToolTip("Text to add after the layer name (before sequence number).")
        naming_layout.addRow("Suffix:", self._suffix_edit)
        
        # Separator
        self._separator_edit = QLineEdit("_")
        self._separator_edit.setMaximumWidth(60)
        self._separator_edit.setToolTip("Character(s) used between name parts.")
        naming_layout.addRow("Separator:", self._separator_edit)
        
        naming_group.setLayout(naming_layout)
        layout.addWidget(naming_group)
        
        # === Export Options Group ===
        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout()
        options_layout.setContentsMargins(8, 8, 8, 8)
        
        # Flatten groups
        self._flatten_groups_checkbox = QCheckBox("Flatten animated groups")
        self._flatten_groups_checkbox.setChecked(True)
        self._flatten_groups_checkbox.setToolTip(
            "Merge group layers into a single flattened image.\n"
            "Useful when a group contains separate line/color layers\n"
            "that should be combined for the final export."
        )
        options_layout.addRow(self._flatten_groups_checkbox)
        
        # Include invisible layers
        self._invisible_checkbox = QCheckBox("Include invisible layers")
        self._invisible_checkbox.setChecked(False)
        self._invisible_checkbox.setToolTip(
            "Export animated layers that are currently hidden in the document."
        )
        options_layout.addRow(self._invisible_checkbox)
        
        # Include reference layers (grey color label)
        self._reference_checkbox = QCheckBox("Include reference layers (grey)")
        self._reference_checkbox.setChecked(False)
        self._reference_checkbox.setToolTip(
            "Export layers marked with a grey color label.\n"
            "These are typically used as animation reference guides."
        )
        options_layout.addRow(self._reference_checkbox)
        
        # Include static (non-animated) layers
        self._static_checkbox = QCheckBox("Include non-animated layers")
        self._static_checkbox.setChecked(False)
        self._static_checkbox.setToolTip(
            "Export layers without animation keyframes as single images.\n"
            "Useful for backgrounds, layouts, peg bars, or safety margins."
        )
        options_layout.addRow(self._static_checkbox)
        
        # Full clip range
        self._full_range_checkbox = QCheckBox("Use full clip range")
        self._full_range_checkbox.setChecked(True)
        self._full_range_checkbox.setToolTip(
            "Export the full animation clip range.\n"
            "Uncheck to export only the selected playback range."
        )
        options_layout.addRow(self._full_range_checkbox)
        
        # Image format selection
        self._image_format_combo = QComboBox()
        self._image_format_combo.addItem("PNG (.png)", "png")
        self._image_format_combo.addItem("Targa (.tga)", "tga")
        self._image_format_combo.setCurrentIndex(0)
        self._image_format_combo.setToolTip("Choose image file format for exported frames.")
        options_layout.addRow("Image format:", self._image_format_combo)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Spacer
        layout.addStretch()
        
        # Dialog buttons
        self._button_box = QDialogButtonBox()
        self._export_button = self._button_box.addButton(
            "Export", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._export_button.setEnabled(False)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        
        layout.addWidget(self._button_box)
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self._browse_button.clicked.connect(self._on_browse)
        self._button_box.accepted.connect(self._on_export)
        self._button_box.rejected.connect(self.reject)
    
    def _load_initial_path(self):
        """Load the initial export path into the UI."""
        if self._export_path and os.path.isdir(self._export_path):
            self._path_edit.setText(self._export_path)
            self._export_button.setEnabled(True)
    
    def _save_export_path(self):
        """Save the current export path to settings."""
        if self._export_path:
            self._settings.setValue(SETTINGS_EXPORT_PATH, self._export_path)
    
    def _update_folder_name_default(self):
        """Set the default folder name based on document name."""
        doc_name = get_document_name(self._document)
        self._folder_name_edit.setText(doc_name)
    
    def _on_browse(self):
        """Handle browse button click."""
        # Start from current path if valid, otherwise use default
        start_path = self._export_path if os.path.isdir(self._export_path) else get_default_export_path()
        
        path = QFileDialog.getExistingDirectory(
            self, 
            "Select Export Directory",
            start_path
        )
        if path:
            self._export_path = path
            self._path_edit.setText(path)
            self._export_button.setEnabled(True)
            # Save immediately when user selects a new path
            self._save_export_path()
    
    def _build_export_path(self) -> str:
        """Build the full export path including subfolder.
        
        Returns:
            Full path to the export folder.
        """
        folder_name = self._folder_name_edit.text().strip()
        if not folder_name:
            folder_name = get_document_name(self._document)
        
        # Sanitize the folder name
        folder_name = sanitize_filename(folder_name)
        
        return os.path.join(self._export_path, folder_name)
    
    def _on_export(self):
        """Handle export button click."""
        document = krita.Krita.instance().activeDocument()
        if not document:
            QMessageBox.warning(
                self,
                "No Document",
                "Please open an animated document before exporting."
            )
            return
        
        # Build the full export path with subfolder
        full_export_path = self._build_export_path()
        
        # Build options from UI state
        options = ExportOptions()
        options.include_invisible = self._invisible_checkbox.isChecked()
        options.include_reference = self._reference_checkbox.isChecked()
        options.include_static = self._static_checkbox.isChecked()
        options.flatten_groups = self._flatten_groups_checkbox.isChecked()
        options.png_compression = DEFAULT_PNG_COMPRESSION
        options.image_format = self._image_format_combo.currentData()
        options.use_full_clip_range = self._full_range_checkbox.isChecked()
        
        # File naming options
        options.file_format = self._format_combo.currentData()
        options.file_prefix = self._prefix_edit.text()
        options.file_suffix = self._suffix_edit.text()
        options.file_separator = self._separator_edit.text() or "_"
        
        # Export folder name (for XDTS file naming)
        options.export_name = self._folder_name_edit.text().strip()
        if not options.export_name:
            options.export_name = get_document_name(document)
        
        # Run export
        self._run_export(document, full_export_path, options)
    
    def _run_export(self, document, export_path: str, options: ExportOptions):
        """Execute the export with progress dialog.
        
        Args:
            document: The Krita document to export.
            export_path: Directory for output files.
            options: Export configuration.
        """
        # Set batch mode to suppress dialogs
        krita.Krita.instance().setBatchmode(True)
        
        # Create progress dialog
        progress = QProgressDialog("Initializing export...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Exporting Animation Layers")
        progress.setWindowModality(get_window_modality())
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        cancelled = False
        
        def on_progress(current, total, message):
            """Update progress dialog."""
            if total > 0:
                progress.setMaximum(total)
                progress.setValue(current)
            progress.setLabelText(message)
            QApplication.processEvents()
        
        def on_cancelled():
            """Check if user cancelled."""
            nonlocal cancelled
            if progress.wasCanceled():
                cancelled = True
            return cancelled
        
        try:
            # Create and configure export engine
            engine = XDTSExportEngine(document, export_path, options)
            engine.on_progress = on_progress
            engine.on_cancelled = on_cancelled
            
            # Run export
            result = engine.export()
            
            progress.close()
            
            # Show result
            if result.success:
                self._show_success_message(result)
                self.accept()
            elif not cancelled:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    f"Export failed: {result.error_message}"
                )
                
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                "Export Error",
                f"An unexpected error occurred:\n\n{str(e)}"
            )
        finally:
            krita.Krita.instance().setBatchmode(False)
    
    def _show_success_message(self, result):
        """Display success notification with option to open output folder.
        
        Args:
            result: The ExportResult from the engine.
        """
        # Try to show floating message in Krita's UI
        try:
            view = krita.Krita.instance().activeWindow().activeView()
            view.showFloatingMessage(
                f"XDTS Export Complete: {result.track_count} tracks",
                krita.Krita.instance().icon("document-save"),
                3000,
                1
            )
        except:
            pass
        
        # Create message box with Open Folder option
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Export Complete")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("XDTS export completed successfully!")
        msg_box.setInformativeText(
            f"Output: {result.output_path}\n"
            f"Tracks exported: {result.track_count}\n"
            f"Total keyframes: {result.frame_count}\n"
            f"Unique frames saved: {result.unique_frames_exported}"
        )
        
        open_folder_btn = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == open_folder_btn:
            folder_path = os.path.dirname(result.output_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
