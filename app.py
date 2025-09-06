import gradio as gr
import os
from PIL import Image
import pandas as pd
import datetime
from radiology_agent import RadiologyAgent

DATA_DIR = "data"

def get_cases():
    return sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))])

def get_phases(case):
    case_path = os.path.join(DATA_DIR, case)
    if not os.path.isdir(case_path):
        return []
    return sorted([d for d in os.listdir(case_path) if os.path.isdir(os.path.join(case_path, d))])

def get_slices(case, phase):
    phase_path = os.path.join(DATA_DIR, case, phase)
    if not os.path.exists(phase_path):
        return []
    return sorted([os.path.join(phase_path, f) for f in os.listdir(phase_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))], key=lambda x: int(os.path.basename(x).split('.')[0]))

def get_slice_image(slice_path):
    return Image.open(slice_path) if slice_path else None

def create_main_app_view(agent):
    cases = get_cases()
    if not cases:
        gr.Markdown("No cases found in the data directory.")
        return None, None, None, None

    case_index = gr.State(0)
    phase_index = gr.State(0)
    slice_index = gr.State(0)

    def get_current_case():
        return cases[case_index.value]

    def get_current_phases():
        return get_phases(get_current_case())

    def get_current_phase():
        phases = get_current_phases()
        if not phases or phase_index.value is None or phase_index.value >= len(phases):
            return None
        return phases[phase_index.value]

    def get_current_slices():
        case = get_current_case()
        phase = get_current_phase()
        if not phase:
            return []
        return get_slices(case, phase)

    def update_image(direction):
        slices = get_current_slices()
        if not slices:
            return None, 0

        current_case_name = get_current_case()
        current_phase_name = get_current_phase()
        current_slice_num = slice_index.value

        new_index = slice_index.value
        if direction == "UP":
            new_index = (slice_index.value - 1 + len(slices)) % len(slices)
        elif direction == "DOWN":
            new_index = (slice_index.value + 1) % len(slices)

        agent.add_interaction({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "case": current_case_name,
            "phase": current_phase_name,
            "action": f"Navigate {direction}",
            "old_slice": current_slice_num,
            "new_slice": new_index,
            "diagnosis": ""
        })

        slice_index.value = new_index
        return get_slice_image(slices[new_index]), new_index

    def update_phase(phase_name):
        phases = get_current_phases()
        if not phase_name or phase_name not in phases:
            phase_index.value = None
            return gr.Image(visible=False), 0
            
        new_phase_index = phases.index(phase_name)

        phase_index.value = new_phase_index
        slice_index.value = 0
        
        agent.add_interaction({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "case": get_current_case(),
            "phase": phase_name,
            "action": "Change Phase",
            "old_slice": -1,
            "new_slice": 0,
            "diagnosis": ""
        })

        slices = get_current_slices()
        image = get_slice_image(slices[0]) if slices else None
        return gr.Image(value=image, visible=True), 0

    def next_case(diagnosis):
        current_case_name = get_current_case()
        current_phase_name = get_current_phase()
        
        if current_phase_name: # Only log if a phase was selected
            agent.add_interaction({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "case": current_case_name,
                "phase": current_phase_name,
                "action": "Diagnosis",
                "old_slice": slice_index.value,
                "new_slice": slice_index.value,
                "diagnosis": diagnosis
            })

        new_case_index = (case_index.value + 1) % len(cases)
        case_index.value = new_case_index
        phase_index.value = None
        slice_index.value = 0

        log_file = agent.save_log_to_excel()
        
        new_phases = get_current_phases()
        
        return gr.Image(visible=False), 0, "", gr.File(value=log_file, visible=True), gr.Radio(choices=new_phases, value=None, label="Phase"), get_current_case()

    with gr.Row():
        with gr.Column():
            image_display = gr.Image(label="Radiology Slice", visible=False)

            with gr.Row():
                case_display = gr.Textbox(label="Current Case", interactive=False)
                phase_radio = gr.Radio(label="Phase")

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
                logout_button = gr.Button("Logout")

    def initial_load():
        phases = get_current_phases()
        return get_current_case(), gr.Radio(choices=phases, value=None, label="Phase")

    up_button.click(lambda: update_image("UP"), outputs=[image_display, slice_num_display])
    down_button.click(lambda: update_image("DOWN"), outputs=[image_display, slice_num_display])
    phase_radio.change(update_phase, inputs=[phase_radio], outputs=[image_display, slice_num_display])
    next_case_button.click(next_case, inputs=[diagnosis_input], outputs=[image_display, slice_num_display, diagnosis_input, log_file_output, phase_radio, case_display])
    download_log_button.click(lambda: agent.save_log_to_excel(), outputs=[log_file_output])
    
    return logout_button, initial_load, case_display, phase_radio


if __name__ == "__main__":
    agent = RadiologyAgent()

    with gr.Blocks() as demo:
        with gr.Group() as login_view:
            gr.Markdown("## Radiology Case Viewer Login")
            username_input = gr.Textbox(label="Username")
            password_input = gr.Textbox(label="Password", type="password")
            login_button = gr.Button("Login")

        with gr.Group(visible=False) as main_app_view:
            logout_button, initial_load_func, case_display_comp, phase_radio_comp = create_main_app_view(agent)

        def login(username, password):
            if agent.login(username, password):
                initial_case, initial_phases = initial_load_func()
                return gr.update(visible=False), gr.update(visible=True), initial_case, initial_phases
            else:
                gr.Warning("Invalid username or password")
                return gr.update(visible=True), gr.update(visible=False), "", gr.Radio(choices=[])

        def logout():
            agent.logout()
            return gr.update(visible=True), gr.update(visible=False)

        login_button.click(login, 
                          inputs=[username_input, password_input], 
                          outputs=[login_view, main_app_view, case_display_comp, phase_radio_comp])
        
        if logout_button:
            logout_button.click(logout, outputs=[login_view, main_app_view])

    demo.launch(share=True)
