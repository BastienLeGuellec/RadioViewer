# Radiology Case Viewer

This is a Gradio-based application for viewing radiology cases, navigating through slices, and entering diagnoses. It logs user interactions and diagnoses to an Excel file for later review.

## Requirements

To run this application, you need Python 3.7+ and the following Python packages:

- `gradio`
- `pandas`
- `openpyxl`

## Installation

1. Clone this repository (if you haven't already).
2. Navigate to the project directory:
   ```bash
   cd /home/bastien/RadioViewer
   ```
3. Install the required Python packages:
   ```bash
   pip install gradio pandas openpyxl
   ```

## Usage

1. Ensure your radiology case data is structured as follows:
   ```
   data/
   ├── case1/
   │   └── non_contrast/
   │       ├── 1.jpg
   │       ├── 2.jpg
   │       └── ...
   ├── case2/
   │   └── non_contrast/
   │       ├── 1.jpg
   │       └── ...
   └── ...
   ```
   Each `caseX` directory should contain a `non_contrast` subdirectory with `.jpg` image slices named numerically (e.g., `1.jpg`, `2.jpg`).

2. Run the application from the project root directory:
   ```bash
   python app.py
   ```

3. Open the displayed local URL in your web browser (e.g., `http://127.0.0.1:7860`).

### Application Features:

- **Navigate Slices:** Use the "UP" and "DOWN" buttons to move through the radiology slices for the current case.
- **Enter Diagnosis:** Type your diagnosis for the current case into the "Diagnosis" textbox.
- **Next Case:** Click "Next Case" to save the current diagnosis and move to the next available case. This action also saves the interaction log to `radiology_log.xlsx`.
- **Download Log:** Click the "Download Log" button to download the `radiology_log.xlsx` file, which contains a record of all slice navigations and diagnoses.
