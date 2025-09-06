import pandas as pd
import os

class RadiologyAgent:
    def __init__(self):
        self.user = None
        self.user_number = None
        self.log_file = None
        self.interaction_log = []
        self.users_df = pd.read_excel("users.xlsx")

    def login(self, username, password):
        if username in self.users_df['username'].values and password == self.users_df[self.users_df['username'] == username]['password'].values[0]:
            self.user = username
            self.user_number = self.users_df[self.users_df['username'] == username].index[0] + 1
            self.log_file = f"{self.user}_radiology_log.xlsx"
            if os.path.exists(self.log_file):
                try:
                    df = pd.read_excel(self.log_file)
                    self.interaction_log = df.to_dict('records') if not df.empty else []
                except Exception as e:
                    print(f"Error loading existing log file, starting fresh: {e}")
                    self.interaction_log = []
            else:
                self.interaction_log = []
            return True
        return False

    def logout(self):
        self.save_log_to_excel()
        self.user = None
        self.user_number = None
        self.log_file = None
        self.interaction_log = []

    def add_interaction(self, interaction):
        interaction['user_number'] = self.user_number
        self.interaction_log.append(interaction)
        self.save_log_to_excel()

    def save_log_to_excel(self):
        if self.interaction_log:
            df = pd.DataFrame(self.interaction_log)
            df.to_excel(self.log_file, index=False)
            print(f"Log saved to {self.log_file}")
        else:
            print("No interactions to log.")
        return self.log_file