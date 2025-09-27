import pandas as pd
import glob

# 🔹 Path to the folder containing Excel files
path = r"C:\Users\user\projects\old\results"   # change this path

# 🔹 Get all Excel files in that folder
all_files = glob.glob("."+ "/*.xlsx")

# 🔹 Read and append all Excel files
df_list = [pd.read_excel(file) for file in all_files]

# 🔹 Concatenate into one dataframe (stacked below each other)
final_df = pd.concat(df_list, ignore_index=True)

# 🔹 Save into a single Excel file
output_file = r"C:\Users\YourName\Documents\merged_file.xlsx"
final_df.to_excel(output_file, index=False)

print("✅ All files merged successfully into:", output_file)
