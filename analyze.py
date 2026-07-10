import os
import sys
import json
import pandas as pd
import numpy as np

# Ensure UTF-8 output in windows terminal
sys.stdout.reconfigure(encoding='utf-8')

# File paths
TX_PATH = r"C:\Users\Computer\Downloads\Ivymoda\BAO CAO\9565e01b_bang_ke_tra_lai_doi_tmdt.csv\9565e01b_bang_ke_tra_lai_doi_tmdt.csv"
SKU_PATH = r"C:\Users\Computer\Downloads\Ivymoda\BAO CAO\all_sku_2026-07-09.csv"

TEMPLATE_PATH = "index_template.html"
OUTPUT_PATH = "index.html"

def get_product_code(ma_vt):
    ma_vt = str(ma_vt).strip()
    if len(ma_vt) >= 9:
        return ma_vt[:2] + ma_vt[4:9]
    return ma_vt

def get_product_line(prod_code):
    if len(prod_code) < 3:
        return "Nhóm hàng khác"
    char3 = prod_code[2]
    if char3.isalpha():
        char_upper = char3.upper()
        if char_upper == 'T':
            return "Nhóm hàng T"
        elif char_upper in ['E', 'D']:
            return "Nhóm hàng Metagent"
        elif char_upper == 'S':
            return "Nhóm hàng Senora"
        elif char_upper == 'A':
            return "Nhóm Quà tặng"
        elif char_upper in ['B', 'H', 'M', 'P']:
            return "Nhóm hàng Moda"
        else:
            return "Nhóm hàng khác"
    else:
        return "Nhóm hàng khác"

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
    else: # pct > 70
        return 'Sale > 70%', f'Sale {pct}%'

def main():
    print("Đang đọc dữ liệu bán hàng (transactions)...")
    if not os.path.exists(TX_PATH):
        print(f"Lỗi: Không tìm thấy tệp dữ liệu bán hàng tại {TX_PATH}")
        sys.exit(1)
        
    df1 = pd.read_csv(TX_PATH, sep='\t', encoding='utf-16')
    print(f"Đọc thành công {len(df1)} dòng bán hàng.")
    
    # Chuyển đổi Ngày Excel sang datetime
    df1['date_parsed'] = pd.to_datetime(df1['Ngày'], unit='D', origin='1899-12-30')
    df1['date_str'] = df1['date_parsed'].dt.strftime('%Y-%m-%d')
    
    # Áp dụng công thức Mã sản phẩm từ cột Mã vt
    df1['product_code'] = df1['Mã vt'].apply(get_product_code)
    
    # Kênh bán hàng từ IVM
    df1['channel_raw'] = df1['IVM'].astype(str).str[3:5]
    channel_map = {'SN': 'Shopee', 'TT': 'TikTok', 'LN': 'Lazada'}
    df1['channel'] = df1['channel_raw'].map(channel_map).fillna('Khác')
    
    # Lấy các cột cần thiết cho transactions
    tx_list = []
    for idx, row in df1.iterrows():
        qty = row['Số lượng'] if 'Số lượng' in row else row.get('SL', 0)
        tx_list.append({
            'date': row['date_str'],
            'sku': str(row['Mã vt']).strip(),
            'product': row['product_code'],
            'qty': int(qty),
            'revenue': float(row['Tiền tổng']),
            'channel': row['channel']
        })
        
    print("Đang đọc dữ liệu tồn kho (SKUs)...")
    if not os.path.exists(SKU_PATH):
        print(f"Lỗi: Không tìm thấy tệp dữ liệu tồn kho tại {SKU_PATH}")
        sys.exit(1)
        
    df2 = pd.read_csv(SKU_PATH, sep=',', encoding='utf-8-sig')
    print(f"Đọc thành công {len(df2)} dòng tồn kho.")
    
    # Loại bỏ dòng tiêu đề lặp lại
    df2 = df2[df2['Ma 16'] != 'Ma 16']
    print(f"Còn lại {len(df2)} SKU sau khi loại bỏ dòng tiêu đề lặp lại.")
    
    # Điền giá trị trống cho tồn kho và chuyển kiểu số
    df2['ON1'] = pd.to_numeric(df2['ON1'], errors='coerce').fillna(0).astype(int)
    df2['ON3'] = pd.to_numeric(df2['ON3'], errors='coerce').fillna(0).astype(int)
    df2['Web'] = pd.to_numeric(df2['Web'], errors='coerce').fillna(0).astype(int)
    df2['Nguyen gia'] = pd.to_numeric(df2['Nguyen gia'], errors='coerce').fillna(0).astype(float)
    df2['Sale'] = pd.to_numeric(df2['Sale'], errors='coerce')
    
    # Làm sạch cột Discount
    df2['clean_discount'] = df2['Discount'].apply(clean_discount)
    
    # Phân loại Chương trình khuyến mãi
    res_prog = df2.apply(classify_sale_program, axis=1)
    df2['program_cat'] = [r[0] for r in res_prog]
    df2['program_detail'] = [r[1] for r in res_prog]
    
    # Dòng sản phẩm & Nhóm sản phẩm
    df2['product_code'] = df2['Ma 7'].astype(str)
    df2['line'] = df2['product_code'].apply(get_product_line)
    df2['group'] = df2['product_code'].apply(get_product_group)
    
    # Chuẩn hóa cột ngày lên hàng
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
            'sale_price': float(row['Sale']) if not pd.isna(row['Sale']) else None,
            'program_cat': row['program_cat'],
            'program_detail': row['program_detail'],
            'launch_date': row['Ngay len hang'],
            'status': row['Trang thai'] if not pd.isna(row['Trang thai']) else ''
        })
        
    print(f"Tổng hợp xong {len(sku_list)} SKU và {len(tx_list)} giao dịch bán hàng.")
    
    # Tạo tệp JSON dữ liệu để kiểm tra hoặc lưu trữ độc lập
    db_data = {
        'transactions': tx_list,
        'skus': sku_list
    }
    
    # Tạo trang dashboard HTML hoàn chỉnh bằng cách chèn dữ liệu vào template
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Lỗi: Không tìm thấy tệp mẫu giao diện tại {TEMPLATE_PATH}")
        sys.exit(1)
        
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    # Chèn dữ liệu dưới dạng chuỗi JSON nén
    json_db_str = json.dumps(db_data, ensure_ascii=False)
    output_content = template_content.replace("// DATABASE_PLACEHOLDER", f"const DATABASE = {json_db_str};")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(output_content)
        
    print(f"Đã tạo thành công trang dashboard tại: {os.path.abspath(OUTPUT_PATH)}")

if __name__ == "__main__":
    main()
