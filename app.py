import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(page_title="Dashboard Fundamental & Valuasi", layout="wide")
st.title("📈 Dashboard Analisis Fundamental & Valuasi")

# ==========================================
# WIDGET INPUT SAHAM
# ==========================================
col1, col2 = st.columns(2)
with col1:
    ticker_symbol = st.text_input("Masukkan Kode Saham (Wajib tambahkan .JK untuk emiten IHSG)", value="BBCA.JK")
with col2:
    periode = st.selectbox("Pilih Periode Laporan Keuangan", ["Tahunan (Annually)", "Kuartalan (Quarterly)"])

if st.button("Analisis Sekarang"):
    try:
        with st.spinner('Menarik data dari server...'):
            # Menarik data dari API Yahoo Finance
            saham = yf.Ticker(ticker_symbol)
            info = saham.info
            
            # Ekstraksi Data Historis (Harga & Laporan)
            hist_1d = saham.history(period="1d")
            if hist_1d.empty:
                st.error("Data harga tidak ditemukan. Pastikan format kode saham benar.")
                st.stop()
            harga_sekarang = hist_1d['Close'].iloc[-1]
            
            if periode == "Tahunan (Annually)":
                income_stmt = saham.financials
                balance_sheet = saham.balance_sheet
            else:
                income_stmt = saham.quarterly_financials
                balance_sheet = saham.quarterly_balance_sheet
                
            if income_stmt.empty or balance_sheet.empty:
                st.warning("Data laporan keuangan tidak tersedia untuk emiten ini.")
                st.stop()
                
            tanggal_terbaru = income_stmt.columns[0]
            
            # Ekstraksi Data Finansial Mentah
            laba_bersih = income_stmt.loc['Net Income'].iloc[0] if 'Net Income' in income_stmt.index else info.get('netIncomeToCommon', 0)
            pendapatan = income_stmt.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income_stmt.index else info.get('totalRevenue', 0)
            beban_total = pendapatan - laba_bersih # Pendekatan sederhana Total Beban
            
            total_aset = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else info.get('totalAssets', 0)
            total_ekuitas = balance_sheet.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in balance_sheet.index else info.get('totalStockholderEquity', 0)
            
            if 'Total Liabilities Net Minority Interest' in balance_sheet.index:
                total_utang = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
            else:
                total_utang = total_aset - total_ekuitas
                
            aset_lancar = balance_sheet.loc['Current Assets'].iloc[0] if 'Current Assets' in balance_sheet.index else 0
            utang_lancar = balance_sheet.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in balance_sheet.index else 0
            
            saham_beredar = info.get('sharesOutstanding', 1) 
            
            # Kalkulasi Rasio
            roa = (laba_bersih / total_aset) * 100 if total_aset else 0
            roe = (laba_bersih / total_ekuitas) * 100 if total_ekuitas else 0
            # Estimasi ROI menggunakan ROIC (Return on Invested Capital)
            modal_diinvestasikan = total_ekuitas + total_utang
            roi = (laba_bersih / modal_diinvestasikan) * 100 if modal_diinvestasikan else 0
            
            eps = laba_bersih / saham_beredar if saham_beredar else 0
            bvps = total_ekuitas / saham_beredar if saham_beredar else 0
            market_cap = harga_sekarang * saham_beredar
            per = harga_sekarang / eps if eps > 0 else 0
            pbv = harga_sekarang / bvps if bvps > 0 else 0
            
            # Indikator Kesehatan
            der = (total_utang / total_ekuitas) if total_ekuitas else 0
            current_ratio = (aset_lancar / utang_lancar) if utang_lancar else 0

            # ==========================================
            # POIN 1 & 2: DESKRIPSI & BIDANG USAHA (HEADER)
            # ==========================================
            nama_perusahaan = info.get('longName', ticker_symbol)
            sektor = info.get('sector', 'Tidak Tersedia')
            industri = info.get('industry', 'Tidak Tersedia')
            deskripsi = info.get('longBusinessSummary', 'Deskripsi perusahaan tidak tersedia.')
            
            st.header(f"{nama_perusahaan}")
            st.caption(f"Sektor: {sektor} | Industri Utama: {industri}")
            st.write(deskripsi)
            st.divider()

            # ==========================================
            # PEMBAGIAN TAB UTAMA
            # ==========================================
            tab1, tab2, tab3 = st.tabs(["📊 Profil & Kinerja (Grafik)", "⚖️ VALUASI OTOMATIS & Kesehatan", "📥 Ekspor Laporan"])
            
            # ------------------------------------------
            # TAB 1: PROFIL & KINERJA GRAFIK (POIN 3, 4, 9)
            # ------------------------------------------
            with tab1:
                col_k1, col_k2 = st.columns(2)
                
                # POIN 4: Struktur Utang, Ekuitas & Pemegang Saham
                with col_k1:
                    st.markdown("### Struktur Modal (Terkini)")
                    st.metric("Total Ekuitas", f"Rp {total_ekuitas:,.0f}")
                    st.metric("Total Utang (Liabilitas)", f"Rp {total_utang:,.0f}")
                
                with col_k2:
                    st.markdown("### Kepemilikan Ekuitas Terbesar")
                    major_holders = saham.major_holders
                    if major_holders is not None and not major_holders.empty:
                        # Perbaikan logika kolom agar tidak error
                        if len(major_holders.columns) == 2:
                            major_holders.columns = ['Persentase', 'Keterangan'] 
                        st.dataframe(major_holders, use_container_width=True, hide_index=True)
                    else:
                        st.info("Data pemegang saham tidak tersedia.")
                        
                st.divider()
                
                # POIN 3: Grafik Total Aset, Pendapatan, Laba Bersih, Beban
                st.markdown("### Grafik Kinerja Keuangan Historis")
                hist_inc = saham.financials
                hist_bal = saham.balance_sheet
                
                if not hist_inc.empty and not hist_bal.empty:
                    df_grafik = pd.DataFrame()
                    
                    df_grafik['Total Aset'] = hist_bal.loc['Total Assets'] if 'Total Assets' in hist_bal.index else pd.Series(dtype=float)
                    df_grafik['Pendapatan'] = hist_inc.loc['Total Revenue'] if 'Total Revenue' in hist_inc.index else pd.Series(dtype=float)
                    df_grafik['Laba Bersih'] = hist_inc.loc['Net Income'] if 'Net Income' in hist_inc.index else pd.Series(dtype=float)
                    df_grafik['Total Beban'] = df_grafik['Pendapatan'] - df_grafik['Laba Bersih']
                    
                    df_grafik = df_grafik.sort_index()
                    
                    fig_kinerja = go.Figure()
                    tahun_labels = df_grafik.index.strftime('%Y')
                    warna = {'Total Aset': '#1f77b4', 'Pendapatan': '#2ca02c', 'Total Beban': '#d62728', 'Laba Bersih': '#ff7f0e'}
                    
                    for kolom in df_grafik.columns:
                        fig_kinerja.add_trace(go.Bar(
                            x=tahun_labels, y=df_grafik[kolom], name=kolom, marker_color=warna[kolom]
                        ))
                    
                    fig_kinerja.update_layout(barmode='group', xaxis_title="Tahun", yaxis_title="Rupiah", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_kinerja, use_container_width=True)
                else:
                    st.info("Data histori laporan keuangan tidak tersedia untuk dibuat grafik.")

            # ------------------------------------------
            # TAB 2: VALUASI OTOMATIS (POIN 5, 6, 7, 8)
            # ------------------------------------------
            with tab2:
                st.markdown(f"## Laporan Analisis & Rekomendasi (Update: {tanggal_terbaru.strftime('%Y-%m-%d')})")
                
                col_v1, col_v2 = st.columns(2)
                
                # POIN 6: Kesehatan Perusahaan (Manajemen, Likuiditas, Solvabilitas)
                with col_v1:
                    st.markdown("### 🏥 Cek Kesehatan Perusahaan")
                    st.write("**Solvabilitas (Debt to Equity Ratio / DER):**")
                    if der > 1:
                        st.warning(f"DER: {der:.2f}x (Risiko Utang Tinggi: Utang melebihi Ekuitas)")
                    else:
                        st.success(f"DER: {der:.2f}x (Sehat: Ekuitas lebih besar dari Utang)")
                        
                    st.write("**Likuiditas (Current Ratio):**")
                    if current_ratio >= 1:
                        st.success(f"CR: {current_ratio:.2f}x (Aman: Aset lancar menutupi utang jangka pendek)")
                    elif current_ratio > 0:
                        st.warning(f"CR: {current_ratio:.2f}x (Waspada: Kesulitan bayar utang jangka pendek)")
                    else:
                        st.info("Data Aset/Utang Lancar tidak tersedia.")
                        
                    st.write("**Efisiensi & Profitabilitas:**")
                    st.metric("ROA (Return on Asset)", f"{roa:.2f}%")
                    st.metric("ROE (Return on Equity)", f"{roe:.2f}%")
                    st.metric("ROI (Return on Investment)", f"{roi:.2f}%")

                # POIN 5 & 7: Kelayakan Beli, Harga Wajar, vs Harga Terkini
                with col_v2:
                    st.markdown("### ⚖️ Valuasi & Rekomendasi Beli")
                    st.metric("Harga Saham Terkini", f"Rp {harga_sekarang:,.0f}")
                    
                    if eps > 0 and bvps > 0:
                        harga_wajar = (22.5 * eps * bvps) ** 0.5
                        st.metric("Estimasi Harga Wajar (Graham)", f"Rp {harga_wajar:,.0f}")
                        
                        margin_of_safety = ((harga_wajar - harga_sekarang) / harga_wajar) * 100
                        
                        if harga_sekarang < harga_wajar:
                            st.success(f"✅ **LAYAK BELI (Undervalued)**")
                            st.write(f"Harga saat ini lebih murah dari harga wajarnya dengan Margin of Safety sebesar **{margin_of_safety:.2f}%**.")
                        else:
                            st.error(f"❌ **TIDAK DIREKOMENDASIKAN (Overvalued)**")
                            st.write(f"Harga saat ini sudah lebih mahal dari estimasi nilai intrinsiknya (Premium **{abs(margin_of_safety):.2f}%**).")
                    else:
                        st.info("Valuasi tidak dapat dihitung otomatis karena EPS atau Nilai Buku bernilai negatif (Perusahaan merugi).")

            # ------------------------------------------
            # TAB 3: EKSPOR LAPORAN (POIN 10)
            # ------------------------------------------
            with tab3:
                st.markdown("### 📥 Tabel Data Keuangan & Rasio Utama")
                st.write("Data di bawah ini siap diekspor untuk kebutuhan dokumentasi laporan.")
                
                df_export = pd.DataFrame({
                    "Indikator": ["Harga Terkini", "Market Cap", "ROA (%)", "ROE (%)", "ROI (%)", "EPS (Laba Per Lembar)", "BVPS (Nilai Buku)", "PER (x)", "PBV (x)"],
                    "Nilai": [harga_sekarang, market_cap, roa, roe, roi, eps, bvps, per, pbv]
                })
                
                st.dataframe(df_export, use_container_width=True)
                
                csv_data = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Format CSV",
                    data=csv_data,
                    file_name=f"Laporan_Fundamental_{ticker_symbol}.csv",
                    mime="text/csv"
                )
                
    except Exception as e:
        st.error(f"Terjadi kendala sistem: {e}")