

# <img src="https://raw.githubusercontent.com/BastienLeGuellec/RadioViewer/refs/heads/main/logo.png" align="left" height="150" width="150" > Radiology Case Viewer

This is a Streamlit-based application for viewing radiology cases, navigating through slices, and entering diagnoses. It includes a login system, case selection dashboard, and logs user interactions and diagnoses to Excel and JSON files for later review.

## Requirements

To run this application, you need Python 3.7+.

## Installation

1.  Clone this repository (if you haven't already).
2.  Navigate to the project directory:
    ```bash
    cd /path/to/RadioViewer
    ```
3.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Prepare User Data:** Ensure you have a `users.xlsx` file in the project root with at least two columns: `username` and `password`.
    Example `users.xlsx`:
    | username | password |
    |----------|----------|
    | user1    | pass1    |
    | user2    | pass2    |

2.  **Prepare Case Data:** Ensure your radiology case data is structured as follows:
    ```
    data/
    ├── case1/
    │   └── non_contrast/
    │       ├── 1.jpg
    │       ├── 2.jpg
    │       └── ...
    ├── case2/
    │   └── arterial/
    │       ├── 1.png
    │       └── ...
    │   └── non_contrast/
    │       ├── 1.jpg
    │       └── ...
    └── ...
    ```
    Each `caseX` directory should contain subdirectories for different series (e.g., `non_contrast`, `arterial`), with image slices named numerically (e.g., `1.jpg`, `2.png`). Supported formats: `.jpg`, `.jpeg`, `.png`.

3.  **Run the application:** From the project root directory, execute:
    ```bash
    streamlit run streamlit_app.py
    ```

4.  Open the displayed local URL in your web browser (e.g., `http://localhost:8501`).

### Application Features:

-   **Login System:** Authenticate users via `users.xlsx`.
-   **Case Selection Dashboard:** View all available cases. Cases you have diagnosed will appear in green, while pending cases will be grey.
-   **Series Navigation:** Select different image series for a case from the sidebar.
-   **Slice Navigation:** Use the "⬆️ Up" and "⬇️ Down" buttons in the sidebar to move through image slices.
-   **Diagnosis Entry:** Enter your diagnosis for the current case in the provided text area.
-   **Save Diagnosis:** Click "Save Diagnosis" to save your entry. This will mark the case as complete for your user and return you to the case selection dashboard.

### Logging and Data Storage:

-   `action_log.xlsx`: Records all user interactions (login, logout, case opening, series selection, slice changes, diagnosis saving).
-   `diagnoses.json`: Stores the diagnoses entered by each user for each case.
