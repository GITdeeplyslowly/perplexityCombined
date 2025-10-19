"""
Launch the GUI for forward testing
"""
import sys
import os

# Add myQuant directory to Python path
myquant_path = os.path.join(os.path.dirname(__file__), 'myQuant')
sys.path.insert(0, myquant_path)

from gui.noCamel1 import MyQuantGUI

if __name__ == "__main__":
    print("🚀 Launching myQuant GUI...")
    app = MyQuantGUI()
    app.mainloop()
