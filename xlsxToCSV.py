import os
import pandas as pd

# Set the folder path where your .xlsx files are stored
input_folder = r"C:\Users\user\projects\PerplexityCombined\myQuant\results"
output_folder = r"C:\Users\user\projects\Perplexity Combined\myQuant\results\csvResults"

# Make sure output folder exists
os.makedirs(output_folder, exist_ok=True)

# Loop through all files in the input folder
for file in os.listdir(input_folder):
    if file.endswith(".xlsx"):
        file_path = os.path.join(input_folder, file)
        
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Convert to .csv with the same filename
        csv_filename = os.path.splitext(file)[0] + ".csv"
        csv_path = os.path.join(output_folder, csv_filename)
        
        # Save as CSV (without index column)
        df.to_csv(csv_path, index=False, encoding="utf-8")
        
        print(f"Converted: {file} -> {csv_filename}")

print("All .xlsx files have been converted to .csv")
