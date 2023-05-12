import tkinter as tk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
from tkinter import *
import ctypes
import platform
import subprocess
import soundfile as sf
import os


class ScrollableLabelFrame(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, bg="white")
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = tk.Frame(self.canvas, bg="white")
        self.interior.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class ToReplace:
    def __init__(self, proj_file, sample_rate, bit_depth, channel_count, replace_file):
        self.proj_file = proj_file
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.channel_count = channel_count
        self.replace_file = replace_file
        self.selected = BooleanVar()



class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=4)
        self.columnconfigure(2, weight=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=6)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=2)

        self.proj_dir_button = Button(self, text="Select Project Directory", command=self.select_proj_dir)
        self.proj_dir_button.grid(column=2, row=0, sticky=tk.E+tk.W, padx=5, pady=5)

        self.proj_dir_labelframe = LabelFrame(self, bg="white")
        self.proj_dir_labelframe.grid(column=0, row=0, sticky=tk.N+tk.S+tk.E+tk.W, columnspan=2, padx=5, pady=5)
        self.proj_dir_label = Label(self.proj_dir_labelframe, text="", bg="white")
        self.proj_dir_label.grid(row=0, column=0, sticky=tk.W)

        self.replace_dir_button = Button(self, text="Select Replace Directory", command=self.select_replace_dir)
        self.replace_dir_button.grid(column=2, row=1, sticky=tk.E+tk.W, padx=5, pady=5)

        self.replace_dir_labelframe = LabelFrame(self, bg="white")
        self.replace_dir_labelframe.grid(column=0, row=1, sticky=tk.N+tk.S+tk.E+tk.W, columnspan=2, padx=5, pady=5)
        self.replace_dir_label = Label(self.replace_dir_labelframe, text="", bg="white")
        self.replace_dir_label.grid(row=0, column=0, sticky=tk.W)

        self.scrollable_frame = ScrollableLabelFrame(self, bg="white")
        self.scrollable_frame.grid(column=0, row=2, sticky=tk.N+tk.S+tk.E+tk.W, columnspan=3, padx=5, pady=5)

        self.find_files_button = Button(self, text="Find Files", command=self.populate_checkboxes)
        self.find_files_button.grid(column=0, row=3, sticky=tk.W+tk.E, padx=5, pady=5)

        self.select_all_button = Button(self, text="Select All", command=self.select_all)
        self.select_all_button.grid(column=2, row=3, sticky=tk.E+tk.W, padx=5)

        self.replace_files_button = Button(self, text="Replace Files", command=self.replace_files)
        self.replace_files_button.grid(column=1, row=3, sticky=tk.W+tk.E, padx=5, pady=5)

        self.status_text = Text(self, height = 5)
        self.status_text.grid(column=0, row=4, sticky=tk.N+tk.S+tk.E+tk.W, columnspan=3, padx=5, pady=5)
        self.status_text.insert(tk.END, "Status")



    def get_wave_file_info(self, file_path):
        with sf.SoundFile(file_path) as sound_file:
            sample_rate = sound_file.samplerate
            bit_depth = sound_file.subtype
            channel_count = sound_file.channels
        return sample_rate, bit_depth, channel_count
        
    def run_ffmpeg(self, input_file, output_file, sample_rate, bit_depth, channel_count):
        # Determine the audio codec to use based on the desired bit depth
        if bit_depth == 'PCM_16':
            audio_codec = 'pcm_s16le'
        elif bit_depth == "PCM_24":
            audio_codec = 'pcm_s24le'
        elif bit_depth == 'FLOAT':
            audio_codec = 'f32le'
        else:
            raise ValueError(f'Invalid bit depth: {bit_depth}. Valid options are 16, 24, or 32.')

        # Construct the command to run ffmpeg
        command = f'ffmpeg -i "{input_file}" -acodec {audio_codec} -ar {str(sample_rate)} -ac {str(channel_count)} -f wav -y "{output_file}" -loglevel quiet'
        # Run the command
        subprocess.run(command, check=True)


    def get_input_files(self, proj_dir, replace_dir): #returns a list of objects that contain the audio info for the file in the sadie project, and the path to the file to replace it with
        # this ignores file extentions
        input_files = []
        proj_files = set(os.listdir(proj_dir))
        replace_files = set(os.listdir(replace_dir))

        for proj_file in proj_files:
            proj_file_name, proj_file_ext = os.path.splitext(proj_file)
            for replace_file in replace_files:
                replace_file_name, replace_file_ext = os.path.splitext(replace_file)
                if proj_file_name == replace_file_name and proj_file_ext == '.wav' :
                    sample_rate, bit_depth, channel_count = self.get_wave_file_info(os.path.join(proj_dir, proj_file))
                    #the .replace makes the file paths readable to ffmpeg
                    input_files.append(ToReplace(os.path.join(proj_dir, proj_file).replace("\\", "/"), sample_rate, bit_depth, channel_count, os.path.join(replace_dir, replace_file).replace("\\", "/")))
        return input_files


    def process_files(self, replace_list): # process all the files in a list of objects, make sure to rename the old file before replaing it 
        processed_count = 0
        skipped_files = []
        if len(replace_list) > 0:
            for i in replace_list:
                #rename the old file, and skip if the renamed file exisists allready
                replace_file_name, replace_file_ext = os.path.splitext(i.proj_file)
                try:
                    os.rename(i.proj_file, replace_file_name + "_old" + replace_file_ext)
                except FileExistsError:
                    skipped_files.append(i.proj_file)
                    continue 
                self.status_text.delete(1.0, tk.END)
                self.status_text.insert(tk.END, "Processing " +  i.proj_file)
                self.status_text.update_idletasks()
                self.run_ffmpeg(i.replace_file, i.proj_file, i.sample_rate, i.bit_depth, i.channel_count)
                processed_count += 1
                self.status_text.delete(1.0, tk.END)
                self.status_text.insert(tk.END, "Compleated " +  i.proj_file)
                self.status_text.update_idletasks()
            #print out the number of files process and the files that were skipped 
            self.final_printout(processed_count, skipped_files)
        else:
            tk.messagebox.showerror(title="Error", message="Please Select Files to Process")    


    def select_proj_dir(self): #open the file dialog to select sadie project folder
        global proj_dir
        proj_dir = filedialog.askdirectory()
        self.proj_dir_label.config(text=proj_dir)

    def select_replace_dir(self): #open the file dialog to choose the folder to relace the files from
        global replace_dir
        replace_dir = filedialog.askdirectory()
        self.replace_dir_label.config(text=replace_dir)

    def populate_checkboxes(self):
        global input_files
        #check that a directory has been selected
        if proj_dir != '' and replace_dir != '':
            input_files = self.get_input_files(proj_dir, replace_dir)
            # Clear existing checkboxes
            for i in self.scrollable_frame.interior.winfo_children():
                i.destroy()
            for file in input_files:
                checkbox = Checkbutton(self.scrollable_frame.interior, text=file.proj_file, variable=file.selected, bg="white")
                checkbox.pack(anchor='w')
        else:
            tk.messagebox.showerror(title="Error", message="Please choose a project and replace Direcoty")

    def select_all(self): # selects all the checkboxes for possable files to replace
        for checkbox in self.scrollable_frame.interior.winfo_children():
            checkbox.select()

    def replace_files(self): # make a list of all the files to process based on what checkboxes are selected 
        replace_list = [file for file in input_files if file.selected.get()]
        self.process_files(replace_list)

    def final_printout(self, processed_count, skipped_files): #after the process runs print out a report in staus_text
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, "processed " +  str(processed_count) + " items \n")
        for i in skipped_files:
            self.status_text.insert(tk.END, "skipped " +  str(i) + ", file has been replaced previously\n")


proj_dir = ''
replace_dir = ''
input_files = []


def make_dpi_aware(): #this needs to be somewhere to make it look nice
    if int(platform.release()) >= 8:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
make_dpi_aware()

if __name__ == "__main__":
    root = Tk()
    root.title("SADiE Fix")
    MainApplication(root).pack(side="top", fill="both", expand=True)
    root.mainloop()


#-------todo---------
#make chckbox bigger 
