import pandas as pd

df = pd.read_excel('C:\\Users\\prueb\\Downloads\\ejemplo_plan.xlsx', sheet_name=0)
print("Columnas:", df.columns.tolist())
print("\nPrimeras 10 filas:")
print(df.head(10).to_string())
print(f"\nTotal filas: {len(df)}")
print(f"\nValores nulos por columna:")
print(df.isnull().sum())
