import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
import os
import re

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Atur directory untuk menyimpan history pengeluaran
history_directory = "data"
if not os.path.exists(history_directory):
    os.makedirs(history_directory)

# Fungsi untuk analisis OCR
def process_receipt(image):
    try:
        text = pytesseract.image_to_string(image)
        text = re.sub(r'(\d), (\d)', r'\1\2', text)  # menghilangkan spasi antar digit dan koma
        text = re.sub(r'(\d),(\d)', r'\1\2', text)  
        # Membersihkan data
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]  # Hapus baris kosong atau whitespace
        return cleaned_lines
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses struk: {e}")
        return []

# Fungsi untuk mengelompokkan barang ke kategori
def categorize_items(items):
    categories = {
        "Makanan": ["beras", "sayur", "daging", "susu", "bread butter pudding", "cream bruille",
                    "choco croissant", "bank of chocolat", "pop mie", "nestle pure life", 
                    "le minerale", "ultra kcng hijau", "nutrtjel", "kanzlr", "knzler", "cheezy", "red bull", "cookie", "cappucinno",
                    "tea", "teh", "meg", "mie", "nasi", "pisang", "tahu", "tempe", "indomie", "belfood", "jeruk", "chocolate", "coffee",
                    "mocha", "telur", "beef", "soto", "cappuccino", "permen", "teh"],
        "Transportasi": ["bensin", "tiket", "tol"],
        "Hiburan": ["bioskop", "game", "streaming", "studio"],
        "Pakaian": ["baju", "sepatu", "jaket", "shirt", "outer"],
        "BodyCare": ["ponds", "autan", "sabun"],
        "Lainnya": ["pensil"]
    }
    categorized_data = {key: [] for key in categories.keys()}
    for item in items:
        item_lower = item.lower()
        for category, keywords in categories.items():
            if any(keyword in item_lower for keyword in keywords):
                categorized_data[category].append(item)
                break
    return categorized_data


# Fungsi untuk menghitung total pengeluaran per kategori
def calculate_totals(categorized_items):
    totals = {}
    for category, items in categorized_items.items():
        total = 0
        for item in items:
            try:
                price_str = item.split()[-1].replace('Rp', '').replace(',', '').replace('.', '')
                if price_str.isdigit():
                    total += float(price_str)
            except (IndexError, ValueError):
                continue
        totals[category] = total
    return totals

# Fungsi untuk memproses total dari struk yang mengandung "Total"
def extract_total_price(items):
    for item in items:
        if "total" in item.lower():
            price_str = item.split()[-1].replace('Rp', '').replace(',', '').replace('.', '')
            if price_str.isdigit():
                return float(price_str)
    return 0

# Fungsi untuk memuat riwayat pengeluaran dari CSV
def load_expenses_history(person_name):
    history_file = os.path.join(history_directory, f"{person_name}_history.csv")
    if os.path.exists(history_file):
        return pd.read_csv(history_file)
    else:
        return pd.DataFrame(columns=["Category", "Amount"])

# Fungsi untuk menyimpan riwayat pengeluaran ke CSV
def save_expenses_history(person_name, data):
    history_file = os.path.join(history_directory, f"{person_name}_history.csv")
    data.to_csv(history_file, index=False)

# Fungsi untuk menghapus riwayat pengeluaran seseorang
def reset_expenses_history(person_name):
    history_file = os.path.join(history_directory, f"{person_name}_history.csv")
    if os.path.exists(history_file):
        os.remove(history_file)
        st.success(f"Riwayat pengeluaran untuk {person_name} telah direset.")
    else:
        st.warning(f"Tidak ada riwayat pengeluaran yang ditemukan untuk {person_name}.")

# Input Anggaran
st.sidebar.header("Pengaturan Anggaran")
budget = st.sidebar.number_input("Masukkan anggaran bulanan (Rp)", min_value=0, value=5000000, step=50000)

# Input Nama Pengguna
st.sidebar.header("Nama Pengguna")
person_name = st.sidebar.text_input("Masukkan nama Anda", "")

# Reset Data User
reset_button = st.sidebar.button("Reset Riwayat Pengeluaran")
if reset_button:
    if person_name:
        reset_expenses_history(person_name)
    else:
        st.warning("Masukkan nama terlebih dahulu sebelum mereset riwayat.")

# Upload dan Analisis Struk
st.header("Unggah dan Analisis Struk Belanja")
uploaded_file = st.file_uploader("Unggah foto struk belanja (format .jpg atau .png)", type=["jpg", "png"])

if person_name and uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Struk yang diunggah", use_column_width=True)

    with st.spinner("Memproses struk..."):
        raw_items = process_receipt(image)

    if raw_items:
        st.subheader("Hasil OCR - Data Produk:")
        st.write(raw_items)

        # Pengelompokkan Pengeluaran
        categorized_data = categorize_items(raw_items)
        st.subheader("Pengelompokkan Barang:")
        for category, items in categorized_data.items():
            st.write(f"**{category}:**")
            for item in items:
                st.write(f"- {item}")

        new_totals = calculate_totals(categorized_data)

        history_df = load_expenses_history(person_name)

        # Hitung total amount yang sudah dikeluarkan
        accumulated_totals = history_df.set_index('Category')['Amount'].to_dict() if not history_df.empty else {}

        # Update total pengeluaran tiap kategori
        for category, total in new_totals.items():
            if category in accumulated_totals:
                accumulated_totals[category] += total 
            else:
                accumulated_totals[category] = total  

        updated_history = pd.DataFrame(list(accumulated_totals.items()), columns=["Category", "Amount"])

        save_expenses_history(person_name, updated_history)

        # Hitung sisa budget
        total_expense_with_history = sum(accumulated_totals.values())
        remaining_budget = budget - total_expense_with_history  

        st.subheader(f"Total Pengeluaran {person_name}:")
        st.write(updated_history)

        st.subheader("Status Anggaran:")
        if remaining_budget < 0:
            st.error(f"Pengeluaran Anda telah melebihi anggaran! Sisa anggaran: Rp {remaining_budget:,.0f}")
        elif remaining_budget <= 0.1 * budget:
            st.warning(f"Pengeluaran Anda mendekati batas anggaran! Sisa anggaran: Rp {remaining_budget:,.0f}")
        else:
            st.success(f"Pengeluaran Anda masih dalam batas aman. Sisa anggaran: Rp {remaining_budget:,.0f}")

        if accumulated_totals:
            largest_category = max(accumulated_totals, key=accumulated_totals.get)
            largest_expenditure = accumulated_totals[largest_category]
            st.subheader("Kategori Pengeluaran Terbesar:")
            st.write(f"**{largest_category}:** {largest_expenditure:,.0f} (Total Pengeluaran)")
