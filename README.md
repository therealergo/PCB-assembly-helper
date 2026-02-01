# PCB Viewer

A Python application for viewing PCB layouts with Pick and Place component highlighting.

## Features

- Load Gerber files (RS-274X format) and render PCB layers
- Load Pick and Place CSV data from Altium Designer
- Switch between Top and Bottom views
- Component table with designator and value columns
- Click on a table row to highlight all components with the same value
- Pan and zoom the PCB view

## Installation

Requires Python 3.10+

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install PySide6 gerbonara
```

## Usage

Run the application:

```bash
python -m pcb_viewer.main
```

Or after installing:

```bash
pcb-viewer
```

### Loading Data

1. Click **Load Gerber Folder...** and select the folder containing your Gerber files
2. Click **Load Pick & Place CSV...** and select your Pick and Place CSV file
3. Use the **Side** dropdown to switch between Top and Bottom views
4. Click on a row in the Components table to highlight those components on the PCB

### Navigation

- **Mouse wheel**: Zoom in/out
- **Click and drag**: Pan the view
- **Zoom to Fit**: Reset view to show entire board

## Supported File Formats

### Gerber Files
- `.GTL` - Top copper layer
- `.GBL` - Bottom copper layer
- `.GTO` - Top silkscreen
- `.GBO` - Bottom silkscreen
- `.GTS` - Top soldermask
- `.GBS` - Bottom soldermask
- `.GM1` - Board outline

### Pick and Place CSV
Standard Altium Designer Pick and Place format with columns:
- Designator
- Comment (component value)
- Layer
- Footprint
- Center-X(mil)
- Center-Y(mil)
- Rotation
- Description
