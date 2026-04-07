import pandas as pd

xl = pd.ExcelFile('C:\\Users\\prueb\\Downloads\\ejemplo_plan.xlsx')
print('Hojas en el archivo:')
for sheet in xl.sheet_names:
    print(f'  - {sheet}')
    df = pd.read_excel('C:\\Users\\prueb\\Downloads\\ejemplo_plan.xlsx', sheet_name=sheet)
    print(f'    Filas: {len(df)}, Columnas: {list(df.columns)}\n')
