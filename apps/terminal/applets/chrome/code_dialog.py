import tkinter as tk
from tkinter import StringVar, messagebox
from tkinter import ttk


class CodeDialog(object):

    def __init__(self, title=None, label="Code Dialog"):
        self.root = tk.Tk()
        self.root.title(title)
        self.code = StringVar()
        mainframe = ttk.Frame(self.root, padding="12 12 12 12")
        mainframe.grid(column=0, row=0, )
        self.label = ttk.Label(mainframe, text=label, width=10)
        self.input = ttk.Entry(mainframe, textvariable=self.code, width=20)
        self.button = ttk.Button(mainframe, text="ok", command=self.click_ok, width=5,)
        self.label.grid(row=1, column=0)
        self.input.grid(row=1, column=1)
        self.button.grid(row=2, column=1, sticky=tk.E)
        self.root.bind('<Return>', self.click_ok)

    def wait_string(self):
        # 局中
        self.root.eval('tk::PlaceWindow . center')
        self.root.mainloop()
        return self.code.get()

    def click_ok(self, *args, **kwargs):
        if not self.code.get():
            messagebox.showwarning(title="warning", message="code is empty")
            return
        self.root.destroy()


if __name__ == '__main__':
    code = CodeDialog(title="Code Dialog", label="Code: ").wait_string()
    print(code)
