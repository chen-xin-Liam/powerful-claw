import sys
sys.path.insert(0, 'd:/powerful-claw')
import customtkinter as ctk
from src.config import theme_manager
from src.ui import customtkinter_app as m

root = ctk.CTk()
root.withdraw()
frame = ctk.CTkFrame(root)
frame.pack()
btn = ctk.CTkButton(frame, text='x')
btn.pack()
root.update()

m.sync_ctk_theme_baseline()
theme_manager.load_all_themes()

_orig_root_conf = root.configure


def trace_root(**kw):
    if 'fg_color' in kw:
        print('CONFIGURE root fg_color <-', kw['fg_color'])
    return _orig_root_conf(**kw)


root.configure = trace_root

ok = m.apply_ctk_theme_hot(root, 'Ocean Blue')
root.update()
print('root final:', root.cget('fg_color'))
print('btn final:', btn.cget('fg_color'))
root.destroy()
