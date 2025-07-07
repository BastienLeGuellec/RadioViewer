import gradio as gr
import os
from PIL import Image
import pandas as pd
import datetime

DATA_DIR = "data"
LOG_FILE = "radiology_log.xlsx"

# Global list to store interaction data
interaction_log = []

def get_cases():
    return sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))])

def get_slices(case):
    non_contrast_path = os.path.join(DATA_DIR, case, "non_contrast")
    if not os.path.exists(non_contrast_path):
        return []
    return sorted([os.path.join(non_contrast_path, f) for f in os.listdir(non_contrast_path) if f.endswith(".jpg")], key=lambda x: int(os.path.basename(x).split('.')[0]))

def get_slice_image(slice_path):
    return Image.open(slice_path) if slice_path else None

def save_log_to_excel():
    if interaction_log:
        df = pd.DataFrame(interaction_log)
        df.to_excel(LOG_FILE, index=False)
        print(f"Log saved to {LOG_FILE}")
    else:
        print("No interactions to log.")
    return LOG_FILE

def create_app():
    cases = get_cases()
    if not cases:
        with gr.Blocks() as demo:
            gr.Markdown("No cases found in the data directory.")
        return demo

    case_index = gr.State(0)
    slice_index = gr.State(0)

    def get_current_case():
        return cases[case_index.value]

    def get_current_slices():
        return get_slices(get_current_case())

    def update_image(direction):
        slices = get_current_slices()
        if not slices:
            return None, 0
        
        current_case_name = get_current_case()
        current_slice_num = slice_index.value

        new_index = slice_index.value
        if direction == "UP": # Corrected logic: UP button moves to higher slice numbers
            new_index = (slice_index.value -1) % len(slices)
        elif direction == "DOWN": # Corrected logic: DOWN button moves to lower slice numbers
            new_index = (slice_index.value + 1 + len(slices)) % len(slices)
        
        # Log the interaction
        interaction_log.append({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "case": current_case_name,
            "action": f"Navigate {direction}",
            "old_slice": current_slice_num,
            "new_slice": new_index,
            "diagnosis": ""
        })

        slice_index.value = new_index
        return get_slice_image(slices[new_index]), new_index

    def next_case(diagnosis):
        current_case_name = get_current_case()
        # Log the diagnosis
        interaction_log.append({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "case": current_case_name,
            "action": "Diagnosis",
            "old_slice": slice_index.value,
            "new_slice": slice_index.value,
            "diagnosis": diagnosis
        })
        
        new_case_index = (case_index.value + 1) % len(cases)
        case_index.value = new_case_index
        slice_index.value = 0
        
        slices = get_current_slices()
        
        # Save log to Excel after each case is completed
        save_log_to_excel()

        return get_slice_image(slices[0]) if slices else None, 0, "", gr.File(value=LOG_FILE, visible=True)

    with gr.Blocks() as demo:
        with gr.Row():
            image_display = gr.Image(label="Radiology Slice")
        
        slice_num_display = gr.Number(label="Slice Number", value=0)

        with gr.Row():
            up_button = gr.Button("UP")
            down_button = gr.Button("DOWN")

        with gr.Row():
            diagnosis_input = gr.Textbox(label="Diagnosis")
            next_case_button = gr.Button("Next Case")

        with gr.Row():
            download_log_button = gr.Button("Download Log")
            log_file_output = gr.File(label="Download Log File", visible=False)

        def initial_load():
            slices = get_current_slices()
            return get_slice_image(slices[0]) if slices else None, 0

        demo.load(initial_load, outputs=[image_display, slice_num_display])
        
        up_button.click(lambda: update_image("UP"), outputs=[image_display, slice_num_display])
        down_button.click(lambda: update_image("DOWN"), outputs=[image_display, slice_num_display])
        next_case_button.click(next_case, inputs=[diagnosis_input], outputs=[image_display, slice_num_display, diagnosis_input, log_file_output])
        download_log_button.click(save_log_to_excel, outputs=[log_file_output])

    return demo

if __name__ == "__main__":
    app = create_app()
    app.launch()