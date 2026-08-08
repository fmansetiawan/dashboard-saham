import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# KONFIGURASI HALAMAN UTAMA
# ==========================================
st.set_page_config(page_title="Sistem Analisis Fundamental", layout="wide")
st.title("Sistem Analisis Fundamental & Valuasi Saham")

# Input Saham
ticker_symbol = st.text_input("Masukkan Kode Saham (Wajib tambahkan .JK untuk emiten IHSG, contoh: ASII.JK)", value="ASII.JK").upper()

if st.button("Eksekusi Analisis"):
    with st.spinner('Menarik data dari bursa...'):
        try:
            saham = yf.Ticker(ticker_symbol)
            info = saham.info
            
            # Tarik Data Keuangan Terbaru (Tahunan)
            keuangan = saham.financials
            neraca = saham.balance_sheet
            
            if keuangan.empty or neraca.empty:
                st.error("Data laporan keuangan tidak tersedia untuk emiten ini.")
                st.stop()
                
            tanggal_laporan = keuangan.columns[0].strftime('%Y-%m-%d')
            harga_sekarang = saham.history(period="1d")['Close'].iloc[-1]
            
            st.divider()

            # ==========================================
            # LOGIKA 1 & 2: PROFIL & BIDANG USAHA
            # ==========================================
            st.header(f"1 & 2. Profil Perusahaan: {info.get('longName', ticker_symbol)}")
            st.markdown(f"**Sektor:** {info.get('sector', '-')} | **Industri Utama:** {info.get('industry', '-')}")
            
            st.markdown("**Deskripsi & Bidang Usaha:**")
            # Catatan: yfinance tidak merinci 'cabang usaha' secara terpisah, semuanya tergabung dalam deskripsi bisnis utama
            st.write(info.get('longBusinessSummary', 'Deskripsi tidak tersedia.'))
            
            st.divider()

            # ==========================================
            # LOGIKA 3: GRAFIK ASET, PENDAPATAN, LABA, BEBAN
            # ==========================================
            st.header("3. Kinerja Finansial (4 Pilar)")
            
            # Ekstraksi Data 4 Tahun Terakhir
            hist_aset = neraca.loc['Total Assets'] if 'Total Assets' in neraca.index else pd.Series(dtype=float)
            hist_pendapatan = keuangan.loc['Total Revenue'] if 'Total Revenue' in keuangan.index else pd.Series(dtype=float)
            hist_laba = keuangan.loc['Net Income'] if 'Net Income' in keuangan.index else pd.Series(dtype=float)
            
            # Estimasi Beban (Jika 'Total Expenses' tidak ada, gunakan Pendapatan - Laba Bersih)
            if 'Total Expenses' in keuangan.index:
                hist_beban = keuangan.loc['Total Expenses']
            else:
                hist_beban = hist_pendapatan - hist_laba

            df_grafik = pd.DataFrame({
                'Total Aset': hist_aset,
                'Pendapatan': hist_pendapatan,
                'Beban Total': hist_beban,
                'Laba Bersih': hist_laba
            }).sort_index()

            fig3 = go.Figure()
            tahun_labels = df_grafik.index.strftime('%Y')
            warna = {'Total Aset': '#1f77b4', 'Pendapatan': '#2ca02c', 'Beban Total': '#d62728', 'Laba Bersih': '#ff7f0e'}
            
            for kolom in df_grafik.columns:
                fig3.add_trace(go.Bar(x=tahun_labels, y=df_grafik[kolom], name=kolom, marker_color=warna[kolom]))
            
            fig3.update_layout(barmode='group', xaxis_title="Tahun", yaxis_title="Rupiah", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig3, use_container_width=True)

            st.divider()

            # ==========================================
            # LOGIKA 4: STRUKTUR UTANG, EKUITAS & KEPEMILIKAN
            # ==========================================
            st.header("4. Struktur Modal & Kepemilikan")
            
            # Ekstraksi data neraca terbaru
            total_aset = hist_aset.iloc[0] if not hist_aset.empty else 0
            total_ekuitas = neraca.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in neraca.index else 0
            
            if 'Total Liabilities Net Minority Interest' in neraca.index:
                total_utang = neraca.loc['Total Liabilities Net Minority Interest'].iloc[0]
            else:
                total_utang = total_aset - total_ekuitas
                
            col4a, col4b = st.columns(2)
            with col4a:
                st.markdown("**Komposisi Modal (Terbaru):**")
                st.metric("Total Utang (Liabilitas)", f"Rp {total_utang:,.0f}")
                st.metric("Total Ekuitas", f"Rp {total_ekuitas:,.0f}")
                
            with col4b:
                st.markdown("**Pemegang Ekuitas Terbesar:**")
                major_holders = saham.major_holders
                if major_holders is not None and not major_holders.empty:
                    if len(major_holders.columns) == 2:
                        major_holders.columns = ['Persentase', 'Keterangan']
                    st.dataframe(major_holders, use_container_width=True, hide_index=True)
                else:
                    st.write("Data kepemilikan tidak tersedia.")
            
            st.divider()

            # ==========================================
            # LOGIKA 6: KESEHATAN PERUSAHAAN (Dihitung sebelum Valuasi)
            # ==========================================
            st.header("6. Kesehatan Perusahaan (Likuiditas & Solvabilitas)")
            
            # Likuiditas: Current Ratio
            aset_lancar = neraca.loc['Current Assets'].iloc[0] if 'Current Assets' in neraca.index else 0
            utang_lancar = neraca.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in neraca.index else 0
            
            cr = (aset_lancar / utang_lancar) if utang_lancar > 0 else 0
            
            # Solvabilitas: Debt to Equity Ratio (DER)
            der = (total_utang / total_ekuitas) if total_ekuitas > 0 else 0
            
            col6a, col6b = st.columns(2)
            with col6a:
                st.metric("Current Ratio (Likuiditas)", f"{cr:.2f}x")
                if cr > 1.5: st.success("Likuiditas Aman (Aset lancar menutupi utang jangka pendek)")
                elif cr > 1: st.warning("Likuiditas Cukup")
                else: st.error("Likuiditas Rentan (Aset lancar < Utang jangka pendek)")
                
            with col6b:
                st.metric("Debt to Equity Ratio / DER (Solvabilitas)", f"{der:.2f}x")
                if der < 1: st.success("Solvabilitas Aman (Modal lebih besar dari utang)")
                elif der < 2: st.warning("Utang Cukup Tinggi")
                else: st.error("Solvabilitas Rentan (Utang jauh lebih besar dari modal)")

            st.divider()

            # ==========================================
            # LOGIKA 5 & 7: KELAYAKAN BELI, PROFITABILITAS, & KOMPARASI HARGA WAJAR
            # ==========================================
            st.header("5 & 7. Profitabilitas & Kesimpulan Valuasi Saham")
            st.caption(f"Menggunakan data laporan keuangan terbaru per: {tanggal_laporan}")
            
            laba_bersih = hist_laba.iloc[0] if not hist_laba.empty else 0
            saham_beredar = info.get('sharesOutstanding', 1)
            
            # Hitung Profitabilitas
            roa = (laba_bersih / total_aset) * 100 if total_aset > 0 else 0
            roe = (laba_bersih / total_ekuitas) * 100 if total_ekuitas > 0 else 0
            # ROI (Return on Invested Capital) didekati dengan ROIC jika tersedia, jika tidak gunakan ROE
            roi = info.get('returnOnCapitalEmployed', roe / 100) * 100
            
            eps = laba_bersih / saham_beredar if saham_beredar > 0 else 0
            bvps = total_ekuitas / saham_beredar if saham_beredar > 0 else 0
            
            # Hitung Harga Wajar (Intrinsic Value menggunakan Graham Number)
            harga_wajar = (22.5 * eps * bvps) ** 0.5 if (eps > 0 and bvps > 0) else 0
            
            col7a, col7b = st.columns(2)
            with col7a:
                st.markdown("**Metrik Profitabilitas:**")
                st.write(f"- **ROA:** {roa:.2f}%")
                st.write(f"- **ROE:** {roe:.2f}%")
                st.write(f"- **ROI (ROIC):** {roi:.2f}%")
                
            with col7b:
                st.markdown("**Komparasi Harga (Real-Time vs Laporan Terbaru):**")
                st.metric("Harga Saham Saat Ini", f"Rp {harga_sekarang:,.0f}")
                st.metric("Harga Wajar (Intrinsic Value)", f"Rp {harga_wajar:,.0f}")
            
            # Logika Kesimpulan "Layak Beli"
            st.markdown("### Kesimpulan Analisis:")
            if harga_wajar == 0:
                st.info("⚠️ Valuasi tidak dapat dihitung karena perusahaan mencetak rugi bersih (EPS negatif). Evaluasi ulang kelayakan investasi.")
            elif harga_sekarang < harga_wajar and roe > 10 and der < 1.5:
                st.success(f"✅ **LAYAK BELI (BUY):** Saham berada di bawah harga wajarnya (Undervalued), memiliki profitabilitas yang baik (ROE > 10%), dan tingkat utang terkendali (DER < 1.5).")
            elif harga_sekarang < harga_wajar:
                st.warning(f"⚖️ **PEMANTAUAN (WATCHLIST):** Saham ini murah secara valuasi, namun perhatikan kualitas fundamental lainnya (ROE saat ini {roe:.2f}% dan DER {der:.2f}x).")
            else:
                st.error(f"❌ **TIDAK LAYAK BELI (MAHAL):** Harga pasar saat ini sudah melampaui harga wajarnya berdasarkan kinerja keuangan terakhir (Overvalued).")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengeksekusi logika analisis: {e}")