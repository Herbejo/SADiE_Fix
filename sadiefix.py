import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
from tkinter import *
import ctypes
import platform
import subprocess
import soundfile as sf
import os



class ScrollableLabelFrame(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = ttk.Frame(self.canvas)
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

proj_dir = ''
replace_dir = ''
input_files = []



def get_wave_file_info(file_path):
    with sf.SoundFile(file_path) as sound_file:
        sample_rate = sound_file.samplerate
        bit_depth = sound_file.subtype
        channel_count = sound_file.channels

    return sample_rate, bit_depth, channel_count
    
def run_ffmpeg(input_file, output_file, sample_rate, bit_depth, channel_count):
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
    command = f'ffmpeg -i "{input_file}" -acodec {audio_codec} -ar {str(sample_rate)} -ac {str(channel_count)} -f wav -y "{output_file}"'



    # Run the command
    subprocess.run(command, check=True)
    print(command)
    



def get_input_files(proj_dir, replace_dir): #returns a list of objects that contain the audio info for the file in the sadie project, and the path to the file to replace it with
    # this ignores file ectentions
    input_files = []
    proj_files = set(os.listdir(proj_dir))
    replace_files = set(os.listdir(replace_dir))

    for proj_file in proj_files:
        proj_file_name, proj_file_ext = os.path.splitext(proj_file)
        for replace_file in replace_files:
            replace_file_name, replace_file_ext = os.path.splitext(replace_file)
            if proj_file_name == replace_file_name and proj_file_ext == '.wav' :
                #print(proj_file_name)
                sample_rate, bit_depth, channel_count = get_wave_file_info(os.path.join(proj_dir, proj_file))
                #the .replace makes the file paths readable to ffmpeg
                input_files.append(ToReplace(os.path.join(proj_dir, proj_file).replace("\\", "/"), sample_rate, bit_depth, channel_count, os.path.join(replace_dir, replace_file).replace("\\", "/")))
    return input_files


def process_files(replace_list): # process all the files in a list of objects, make sure to rename the old file before replaing it 
    print(len(replace_list))
    
    for i in replace_list:
        ##
        # do somthing here to rename old file 
        #print(i.proj_file)
        status_text.delete(1.0, tk.END)
        status_text.insert(tk.END, "pcocessing " +  i.proj_file)
        status_text.update_idletasks()
        run_ffmpeg(i.replace_file, i.proj_file, i.sample_rate, i.bit_depth, i.channel_count)
        status_text.delete(1.0, tk.END)
        status_text.insert(tk.END, "compleated " +  i.proj_file)
        status_text.update_idletasks()
        #log here
    status_text.delete(1.0, tk.END)
    status_text.insert(tk.END, "processed " +  str(len(replace_list)) + " items")
    

def make_dpi_aware(): ##this needs to be somewhere to make it look nice
    if int(platform.release()) >= 8:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
     
make_dpi_aware()


def select_proj_dir():
    global proj_dir
    proj_dir = filedialog.askdirectory()
    proj_dir_label.config(text=proj_dir)

def select_replace_dir():
    global replace_dir
    replace_dir = filedialog.askdirectory()
    replace_dir_label.config(text=replace_dir)

def populate_checkboxes():
    global input_files
    input_files = get_input_files(proj_dir, replace_dir)

    for file in input_files:
        checkbox = Checkbutton(scrollable_frame.interior, text=file.proj_file, variable=file.selected)
        checkbox.pack(anchor='w')

def select_all():
    for checkbox in scrollable_frame.interior.winfo_children():
        checkbox.select()

def replace_files():
    replace_list = [file for file in input_files if file.selected.get()]
    process_files(replace_list)



root = Tk()

proj_dir = ""
replace_dir = ""
input_files = []

proj_dir_button = Button(root, text="Select Project Directory", command=select_proj_dir)
proj_dir_button.pack()

proj_dir_label = Label(root, text="")
proj_dir_label.pack()

replace_dir_button = Button(root, text="Select Replace Directory", command=select_replace_dir)
replace_dir_button.pack()

replace_dir_label = Label(root, text="")
replace_dir_label.pack()

scrollable_frame = ScrollableLabelFrame(root, )
scrollable_frame.pack()

find_files_button = Button(root, text="Find Files", command=populate_checkboxes)
find_files_button.pack()

select_all_button = Button(root, text="Select All", command=select_all)
select_all_button.pack()

replace_files_button = Button(root, text="Replace Files", command=replace_files)
replace_files_button.pack()

status_text = Text(root, height = 5)
status_text.pack()
status_text.insert(tk.END, "Status")

root.mainloop()

    
    
    
#-------todo---------
#tidy up make gui
#make it check for length 
#select all button
#make chckbox bigger 