import os
import sys
import json
import re
import pandas as pd
import numpy as np
import zipfile
import io

sys.stdout.reconfigure(encoding='utf-8')

# File paths from the user's computer
TX_PATH = r"C:\Users\Computer\Downloads\Ivymoda\BAO CAO\9cc17914_bang_ke_hoa_don_doi_tmdt.csv\9cc17914_bang_ke_hoa_don_doi_tmdt.csv"
RET_PATH = r"C:\Users\Computer\Downloads\Ivymoda\BAO CAO\de804070_bang_ke_tra_lai_doi_tmdt.csv\de804070_bang_ke_tra_lai_doi_tmdt.csv"
SKU_PATH = r"C:\Users\Computer\Downloads\Ivymoda\BAO CAO\all_sku_2026-07-12.csv"
if not os.path.exists(SKU_PATH):
    SKU_PATH = r"C:\Users\Computer\Downloads\Ivymoda\BAO CAO\all_sku_2026-07-09.csv"

TEMPLATE_PATH = "index_template.html"
OUTPUT_PATH = "index.html"

def get_product_code(ma_vt):
    ma_vt = str(ma_vt).strip()
    match = re.match(r'^(\d{2})([a-zA-Z]\d{4})$', ma_vt)
    if match:
        return match.group(1) + match.group(2).upper()
        
    match = re.search(r'(\d{2}).{2}([a-zA-Z]\d{4})', ma_vt)
    if match:
        return match.group(1) + match.group(2).upper()
        
    return None

def get_product_line(product_code):
    lines = {
        'M': 'Nhóm hàng Menswear',
        'K': 'Nhóm hàng Kids',
        'S': 'Nhóm hàng Senora'
    }
    first_char = str(product_code)[0].upper()
    second_char = str(product_code)[1].upper() if len(str(product_code)) > 1 else ''
    
    if first_char in lines:
        return lines[first_char]
    if first_char.isdigit():
        if second_char in lines:
            return lines[second_char]
        return 'Nhóm hàng Moda'
    return 'Nhóm hàng Moda'

def load_dataframe(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    
    # Try reading as zip first
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path, 'r') as z:
            csv_files = [f for f in z.namelist() if f.lower().endswith('.csv')]
            if csv_files:
                with z.open(csv_files[0]) as f:
                    try:
                        return pd.read_csv(io.TextIOWrapper(f, encoding='utf-8-sig'), low_memory=False)
                    except:
                        f.seek(0)
                        return pd.read_csv(io.TextIOWrapper(f, encoding='utf-16le'), sep='\t', low_memory=False)
    
    # Normal reading
    try:
        return pd.read_csv(path, low_memory=False)
    except:
        try:
            return pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
        except:
            return pd.read_csv(path, encoding='utf-16le', sep='\t', low_memory=False)

def parse_date(val):
    try:
        # If it's a number (Excel serial)
        fval = float(val)
        if fval > 40000:
            return pd.to_datetime('1899-12-30') + pd.to_timedelta(fval, unit='D')
    except:
        pass
    return pd.to_datetime(val, errors='coerce')

def get_product_group(prod_code):
    prefix2 = prod_code[:2]
    if prefix2.isdigit():
        val = int(prefix2)
        if 10 <= val <= 19:
            return "Nhóm Áo"
        elif 20 <= val <= 29:
            return "Nhóm Quần"
        elif 30 <= val <= 32:
            return "Chân váy"
        elif 39 <= val <= 49:
            return "Nhóm Đầm"
        elif 56 <= val <= 58:
            return "Áo thun"
        elif 60 <= val <= 68:
            return "Áo vest"
        elif 70 <= val <= 79:
            return "Áo khoác"
        else:
            return "Nhóm sản phẩm khác"
    else:
        return "Nhóm sản phẩm khác"

def clean_discount(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().lower()
    if s.endswith('d') or s.endswith('đ'):
        s = s[:-1].strip()
    try:
        return float(s)
    except:
        return np.nan

def classify_sale_program(row):
    s = row['Sale']
    orig = row['Nguyen gia']
    
    if pd.isna(s) or s == 0 or s == orig:
        return 'Chương trình Nguyên giá', 'Nguyên giá'
    
    pct = round((1 - s / orig) * 100) if orig > 0 else 0
    
    if pct < 30:
        return 'Chương trình Nguyên giá', 'Nguyên giá'
    elif 30 <= pct < 50:
        return 'Sale từ 30 - 50%', f'Sale {pct}%'
    elif 50 <= pct <= 70:
        return 'Sale 50 - 70%', f'Sale {pct}%'
    else:
        return 'Sale > 70%', f'Sale {pct}%'

def process_tx_file(path):
    if not os.path.exists(path):
        print(f"Cảnh báo: Không tìm thấy {path}")
        return []
    
    df = pd.read_csv(path, sep='\t', encoding='utf-16')
    df['date_parsed'] = pd.to_datetime(df['Ngày'], unit='D', origin='1899-12-30', errors='coerce')
    # If standard date parsing failed, try string parsing
    mask = df['date_parsed'].isna()
    if mask.any():
        df.loc[mask, 'date_parsed'] = pd.to_datetime(df.loc[mask, 'Ngày'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    
    df['date_str'] = df['date_parsed'].dt.strftime('%Y-%m-%d')
    df['product_code'] = df['Mã vt'].astype(str).apply(get_product_code)
    df = df.dropna(subset=['product_code'])
    
    df['channel_raw'] = df['IVM'].astype(str).str[3:5]
    channel_map = {'SN': 'Shopee', 'TT': 'TikTok', 'LN': 'Lazada'}
    df['channel'] = df['channel_raw'].map(channel_map).fillna('Khác')
    
    res = []
    for idx, row in df.iterrows():
        qty = row.get('Số lượng', row.get('SL', 0))
        res.append({
            'date': row['date_str'] if pd.notna(row['date_str']) else '2026-06-01',
            'sku': str(row['Mã vt']).strip(),
            'product': row['product_code'],
            'qty': int(qty) if pd.notna(qty) else 0,
            'revenue': float(row['Tiền tổng']) if pd.notna(row['Tiền tổng']) else 0.0,
            'channel': row['channel']
        })
    return res

def main():
    print("Đang đọc dữ liệu Bán Hàng...")
    tx_list = process_tx_file(TX_PATH)
    print(f"-> Đọc được {len(tx_list)} đơn hàng.")
    
    print("Đang đọc dữ liệu Hàng Hoàn...")
    ret_list = process_tx_file(RET_PATH)
    print(f"-> Đọc được {len(ret_list)} đơn hoàn.")

    print("Đang đọc dữ liệu Tồn Kho (SKU)...")
    if not os.path.exists(SKU_PATH):
        print("Không tìm thấy file Bảng kê bán hàng.")
        sys.exit(1)
        
    df2 = load_dataframe(SKU_PATH)

    df2 = df2[df2['Ma 16'] != 'Ma 16']
    
    df2['ON1'] = pd.to_numeric(df2['ON1'], errors='coerce').fillna(0).astype(int)
    df2['ON3'] = pd.to_numeric(df2['ON3'], errors='coerce').fillna(0).astype(int)
    df2['Web'] = pd.to_numeric(df2['Web'], errors='coerce').fillna(0).astype(int)
    df2['Nguyen gia'] = pd.to_numeric(df2['Nguyen gia'], errors='coerce').fillna(0).astype(float)
    df2['Sale'] = pd.to_numeric(df2['Sale'], errors='coerce')
    
    res_prog = df2.apply(classify_sale_program, axis=1)
    df2['program_cat'] = [r[0] for r in res_prog]
    df2['program_detail'] = [r[1] for r in res_prog]
    
    df2['product_code'] = df2['Ma 7'].astype(str).apply(get_product_code)
    mask = df2['product_code'].isna()
    if mask.any():
        df2.loc[mask, 'product_code'] = df2.loc[mask, 'Ma 16'].astype(str).apply(get_product_code)
    df2 = df2.dropna(subset=['product_code'])
    
    df2['line'] = df2['product_code'].apply(get_product_line)
    df2['group'] = df2['product_code'].apply(get_product_group)
    df2['Ngay len hang'] = df2['Ngay len hang'].fillna('')
    
    sku_list = []
    for idx, row in df2.iterrows():
        sku_list.append({
            'sku': str(row['Ma 16']).strip(),
            'product': row['product_code'],
            'line': row['line'],
            'group': row['group'],
            'on1': int(row['ON1']),
            'on3': int(row['ON3']),
            'web': int(row['Web']),
            'original_price': float(row['Nguyen gia']),
            'sale_price': float(row['Sale']) if pd.notna(row['Sale']) else None,
            'program_cat': row['program_cat'],
            'program_detail': row['program_detail'],
            'launch_date': row['Ngay len hang'],
            'status': row['Trang thai'] if pd.notna(row['Trang thai']) else ''
        })
    print(f"-> Đọc được {len(sku_list)} mã SKU.")
    
    db_data = {
        'transactions': tx_list,
        'returns': ret_list,
        'skus': sku_list
    }
    
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Lỗi: Không tìm thấy {TEMPLATE_PATH}")
        sys.exit(1)
        
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    json_db_str = json.dumps(db_data, ensure_ascii=False)
    
    # Replace the placeholder OR the old JSON assignment
    import re
    if "// DATABASE_PLACEHOLDER" in template_content:
        output_content = template_content.replace("// DATABASE_PLACEHOLDER", f"const DATABASE = {json_db_str};")
    else:
        output_content = re.sub(r'const DATABASE = \{[\s\S]*?\};', lambda m: f"const DATABASE = {json_db_str};", template_content)

    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(output_content)
        
    print("HOÀN TẤT!")

if __name__ == "__main__":
    main()
