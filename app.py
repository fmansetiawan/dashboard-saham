import plotly.graph_objects as go
import io
import streamlit as st
import yfinance as yf
import pandas as pd

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Fundamental Real-Time", layout="wide")
st.title("📈 Dashboard Analisis Fundamental & Valuasi Real-Time")
st.write("Menggabungkan laporan keuangan dengan harga pasar terkini.")

# 1. Input dari Pengguna
col1, col2 = st.columns(2)
with col1:
    # Contoh BBCA.JK untuk saham BCA di IHSG
    ticker_symbol = st.text_input("Masukkan Kode Saham (tambahkan .JK untuk IHSG)", value="BBRI.JK")
with col2:
    periode = st.selectbox("Pilih Periode Laporan Keuangan", ["Tahunan (Annually)", "Kuartalan (Quarterly)"])

if st.button("Analisis Sekarang"):
    try:
        # Menarik data dari Yahoo Finance
        saham = yf.Ticker(ticker_symbol)
        info = saham.info
        
        # Mengambil harga terkini
        harga_sekarang = saham.history(period="1d")['Close'].iloc[-1]
        
        # 2. Mengambil Laporan Keuangan sesuai pilihan
        if periode == "Tahunan (Annually)":
            income_stmt = saham.financials
            balance_sheet = saham.balance_sheet
        else:
            income_stmt = saham.quarterly_financials
            balance_sheet = saham.quarterly_balance_sheet
            
        # Mengambil kolom data terbaru
        tanggal_terbaru = income_stmt.columns[0]
        
        # 3. Ekstraksi Data Mentah
        # Gunakan dict .get() untuk menghindari error jika data kosong
        laba_bersih = income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else info.get('netIncomeToCommon', 0)
        total_aset = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else info.get('totalAssets', 0)
        total_ekuitas = balance_sheet.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in balance_sheet.index else info.get('totalStockholderEquity', 0)
        saham_beredar = info.get('sharesOutstanding', 1) # Mencegah pembagian dengan nol
        
        # 4. Kalkulasi Data Fundamental (Statis)
        roa = (laba_bersih / total_aset) * 100 if total_aset else 0
        roe = (laba_bersih / total_ekuitas) * 100 if total_ekuitas else 0
        eps = laba_bersih / saham_beredar
        bvps = total_ekuitas / saham_beredar # Book Value Per Share
        
        # 5. Kalkulasi Data Valuasi (Real-time dengan harga sekarang)
        market_cap = harga_sekarang * saham_beredar
        per = harga_sekarang / eps if eps > 0 else 0
        pbv = harga_sekarang / bvps if bvps > 0 else 0
        
        # --- TAMPILAN DASHBOARD ---
        st.subheader(f"Harga Terkini {ticker_symbol}: Rp {harga_sekarang:,.0f}")
        st.caption(f"Berdasarkan laporan keuangan per: {tanggal_terbaru.strftime('%Y-%m-%d')}")
        
        st.markdown("### 📊 Valuasi Pasar (Real-Time)")
        met1, met2, met3 = st.columns(3)
        met1.metric("Market Cap", f"Rp {market_cap:,.0f}")
        met2.metric("PER (Price to Earnings)", f"{per:.2f}x")
        met3.metric("PBV (Price to Book)", f"{pbv:.2f}x")
        
        st.markdown("### 🏢 Kinerja Keuangan (Statis)")
        met4, met5, met6, met7 = st.columns(4)
        met4.metric("ROA (Return on Assets)", f"{roa:.2f}%")
        met5.metric("ROE (Return on Equity)", f"{roe:.2f}%")
        met6.metric("EPS (Laba Per Lembar)", f"Rp {eps:,.2f}")
        met7.metric("BVPS (Nilai Buku)", f"Rp {bvps:,.2f}")
        
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil data. Pastikan kode saham benar atau coba lagi. Detail: {e}")
# ... (letakkan di bawah baris st.metric BVPS dari kode sebelumnya) ...
        
        st.divider()
        
        # Membuat Tab Menu
        tab1, tab2, tab3 = st.tabs(["📈 Grafik Interaktif", "⚖️ Valuasi Otomatis", "📥 Ekspor Laporan"])
        
        # --- TAB 1: VISUALISASI INTERAKTIF ---
        with tab1:
            st.markdown(f"### Pergerakan Harga {input_saham} (6 Bulan Terakhir)")
            hist_6m = saham.history(period="6mo")
            
            # Membuat grafik interaktif dengan Plotly
            fig = go.Figure(data=go.Scatter(
                x=hist_6m.index, 
                y=hist_6m['Close'], 
                mode='lines', 
                name='Harga Tutup',
                line=dict(color='#17B169', width=2)
            ))
            fig.update_layout(xaxis_title="Tanggal", yaxis_title="Harga (Rp)", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # --- TAB 2: VALUASI OTOMATIS (GRAHAM NUMBER) ---
        with tab2:
            st.markdown("### Kalkulator Nilai Wajar (Intrinsic Value)")
            st.caption("Menggunakan metode Graham Number untuk saham defensif.")
            
            # Rumus Graham Number: Akar dari (22.5 x EPS x BVPS)
            if eps > 0 and bvps > 0:
                graham_number = (22.5 * eps * bvps) ** 0.5
                st.metric("Nilai Wajar (Graham Number)", f"Rp {graham_number:,.0f}")
                
                # Logika Penilaian
                if harga_sekarang < graham_number:
                    st.success(f"✅ **Undervalued!** Harga pasar (Rp {harga_sekarang:,.0f}) lebih murah dari nilai wajarnya.")
                else:
                    st.warning(f"⚠️ **Overvalued!** Harga pasar (Rp {harga_sekarang:,.0f}) sudah lebih mahal dari nilai wajarnya.")
            else:
                st.info("Nilai wajar tidak dapat dihitung karena EPS atau BVPS bernilai negatif.")

        # --- TAB 3: EKSPOR LAPORAN ---
        with tab3:
            st.markdown("### Unduh Ringkasan Fundamental")
            st.write("Simpan ringkasan analisis hari ini ke dalam format CSV/Excel.")
            
            # Membungkus hasil ke dalam tabel
            df_export = pd.DataFrame({
                "Indikator": ["Harga Terkini", "Market Cap", "EPS", "BVPS", "PER (x)", "PBV (x)", "ROA (%)", "ROE (%)"],
                "Nilai": [harga_sekarang, market_cap, eps, bvps, per, pbv, roa, roe]
            })
            
            st.dataframe(df_export, use_container_width=True)
            
            # Tombol Download
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data CSV",
                data=csv_data,
                file_name=f"Laporan_{input_saham}_Fundamental.csv",
                mime="text/csv"
            )