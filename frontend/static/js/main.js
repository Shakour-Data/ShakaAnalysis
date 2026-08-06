// Financial Dashboard - Main JavaScript
// Location: frontend/static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard Initialization...');
    
    // ======================
    // ELEMENT REFERENCES
    // ======================
    const symbolInput = document.getElementById('symbolInput');
    const symbolDropdown = document.getElementById('symbolDropdown');
    const dateRangeSelect = document.getElementById('dateRange');
    const chartTypeSelect = document.getElementById('chartType');
    const fetchBtn = document.getElementById('fetchDataBtn');
    const loadDataBtn = document.getElementById('loadDataBtn');
    const analysisEditor = document.getElementById('analysisEditor');
    const saveBtn = document.getElementById('saveAnalysisBtn');
    const postBtn = document.getElementById('postAnalysisBtn');
    const saveStatus = document.getElementById('saveStatus');
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    // Indicator values
    const rsiValue = document.getElementById('rsiValue');
    const macdValue = document.getElementById('macdValue');
    const sma20Value = document.getElementById('sma20Value');
    const sma50Value = document.getElementById('sma50Value');
    const priceRangeValue = document.getElementById('priceRangeValue');
    const volumeValue = document.getElementById('volumeValue');
    
    // Download buttons
    const downloadPrice = document.getElementById('downloadPrice');
    const downloadIndicators = document.getElementById('downloadIndicators');
    const downloadFull = document.getElementById('downloadFull');
    
    // Chart canvas
    const priceChartCanvas = document.getElementById('priceChartCanvas');
    const rsiChartCanvas = document.getElementById('rsiChart');
    const macdChartCanvas = document.getElementById('macdChart');
    
    // Toggle indicator buttons
    const toggleButtons = document.querySelectorAll('.toggle-indicator');
    
    // ======================
    // STATE VARIABLES
    // ======================
    let currentSymbol = '';
    let currentData = [];
    let priceTable = null;
    let priceChart = null;
    let rsiChart = null;
    let macdChart = null;
    let processing = false;
    const visibleIndicators = {
        rsi: false,
        macd: false,
        bbands: false
    };
    
    // ======================
    // SACRED COLOR PALETTE (Harmonic Design Tokens)
    // ======================
    const COLORS = {
        gevurah: '#C62828',
        chesed: '#1565C0',
        yesod: '#F5F5F5',
        tiferet: '#FFD54F',
        success: '#10b981',
        danger: '#EF5350'
    };
    
    const rgb = (hex) => {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgb(${r}, ${g}, ${b})`;
    };
    
    const rgba = (hex, alpha) => `rgba(${rgb(hex).match(/\d+/g).map(n => n).join(', ')}, ${alpha})`;
    
    // ======================
    // UTILITY FUNCTIONS
    // ======================
    const formatPrice = (value, decimals = 2) => {
        if (value === null || value === undefined || isNaN(value)) return '--';
        return parseFloat(value).toLocaleString('fa-IR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    };
    
    const formatVolume = (value) => {
        if (value === null || value === undefined || isNaN(value)) return '--';
        return parseFloat(value).toLocaleString('fa-IR');
    };
    
    const formatRSI = (value) => {
        if (value === null || value === undefined || isNaN(value)) return '--';
        return parseFloat(value).toFixed(2);
    };
    
    const formatMACD = (value) => {
        if (value === null || value === undefined || isNaN(value)) return '--';
        return parseFloat(value).toFixed(4);
    };
    
    const getDateRangeYears = (range) => {
        const years = { '1y': 1, '2y': 2, '3y': 3, '4y': 4, 'all': 10 };
        return years[range] || 0;
    };
    
    const showLoading = (show) => {
        if (show) {
            loadingOverlay.classList.add('show');
            fetchBtn.disabled = true;
            loadDataBtn.disabled = true;
        } else {
            loadingOverlay.classList.remove('show');
            fetchBtn.disabled = false;
            loadDataBtn.disabled = false;
        }
    };
    
    const showStatus = (message, isError = false) => {
        saveStatus.textContent = message;
        saveStatus.className = isError ? 'text-danger' : 'text-success';
        saveStatus.style.display = 'block';
        setTimeout(() => { saveStatus.style.display = 'none'; }, 3000);
    };
    
    // ======================
    // SYMBOL LOADING
    // ======================
    const loadSymbols = async () => {
        try {
            const response = await fetch('/api/symbols');
            const symbols = await response.json();
            
            symbolDropdown.innerHTML = '';
            symbols.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = symbol;
                symbolDropdown.appendChild(option);
            });
            
            // Pre-select first symbol if available
            if (symbols.length > 0 && !symbolInput.value) {
                symbolInput.value = symbols[0];
                symbolInput.dispatchEvent(new Event('change'));
            }
        } catch (e) {
            console.error('Error loading symbols:', e);
        }
    };
    
    // ======================
    // FETCH DATA
    // ======================
    const fetchData = async () => {
        if (processing) return;
        
        const symbol = symbolInput.value.trim();
        if (!symbol) {
            showStatus('لطفاً نام سهم یا شاخص را وارد کنید', true);
            return;
        }
        
        processing = true;
        currentSymbol = symbol;
        showLoading(true);
        
        try {
            // Get date range
            const dateRange = dateRangeSelect.value;
            const years = getDateRangeYears(dateRange);
            
            const endDate = new Date();
            const startDate = new Date();
            startDate.setFullYear(startDate.getFullYear() - years);
            
            // Format dates
            const startStr = startDate.toISOString().slice(0, 10);
            const endStr = endDate.toISOString().slice(0, 10);
            
            // Fetch data from API
            const response = await fetch(`/api/data/${encodeURIComponent(symbol)}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'داده یافت نشد');
            }
            
            const data = await response.json();
            currentData = data;
            
            // Process and display
            processData();
            
        } catch (error) {
            console.error('Error fetching data:', error);
            showStatus('خطا در بارگذاری داده‌ها: ' + error.message, true);
        } finally {
            processing = false;
            showLoading(false);
        }
    };
    
    // ======================
    // PROCESS DATA
    // ======================
    const processData = () => {
        if (!currentData || currentData.length === 0) return;
        
        // Sort by date
        currentData.sort((a, b) => new Date(a.Date) - new Date(b.Date));
        
        // Update table
        updatePriceTable();
        
        // Update indicators
        updateIndicatorCards();
        
        // Update charts
        updateCharts();
    };
    
    // ======================
    // PRICE TABLE
    // ======================
    const updatePriceTable = () => {
        const tbody = document.querySelector('#priceTable tbody');
        tbody.innerHTML = '';
        
        // Use all data but limit to last 500 for performance
        const displayData = currentData.slice(-500);
        
        displayData.forEach(row => {
            const tr = document.createElement('tr');
            
            const close = parseFloat(row.Close);
            const open = parseFloat(row.Open);
            const change = close - open;
            const changeClass = change >= 0 ? 'price-up' : 'price-down';
            const changeIcon = change >= 0 ? '▲' : '▼';
            
            tr.innerHTML = `
                <td>${row.Date}</td>
                <td class="text-end">${formatPrice(open)}</td>
                <td class="text-end">${formatPrice(parseFloat(row.High))}</td>
                <td class="text-end">${formatPrice(parseFloat(row.Low))}</td>
                <td class="text-end ${changeClass}">${formatPrice(close)} ${changeIcon}</td>
                <td class="text-end">${formatVolume(row.Volume)}</td>
                <td class="text-end">${formatMACD(row.MACD)}</td>
                <td class="text-end">${formatRSI(row.RSI)}</td>
            `;
            
            tbody.appendChild(tr);
        });
        
        // Initialize DataTable
        if (priceTable) {
            priceTable.clear().rows.add($(tbody).children()).draw();
        } else {
            priceTable = $('#priceTable').DataTable({
                paging: true,
                lengthChange: false,
                searching: false,
                ordering: false,
                info: true,
                responsive: true,
                pageLength: 20,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fa.json'
                }
            });
        }
    };
    
    // ======================
    // INDICATOR CARDS
    // ======================
    const updateIndicatorCards = () => {
        if (!currentData || currentData.length === 0) return;
        
        const last = currentData[currentData.length - 1];
        
        // RSI
        const rsi = parseFloat(last.RSI);
        if (!isNaN(rsi)) {
            rsiValue.textContent = formatRSI(rsi);
            rsiValue.className = 'indicator-value ' + 
                (rsi >= 70 ? 'overbought' : rsi <= 30 ? 'oversold' : 'neutral');
        } else {
            rsiValue.textContent = '--';
            rsiValue.className = 'indicator-value neutral';
        }
        
        // MACD
        const macd = parseFloat(last.MACD);
        const signal = parseFloat(last.Signal);
        if (!isNaN(macd) && !isNaN(signal)) {
            macdValue.textContent = formatMACD(macd);
            macdValue.className = 'indicator-value ' + (macd > signal ? 'bullish' : 'bearish');
        } else {
            macdValue.textContent = '--';
            macdValue.className = 'indicator-value neutral';
        }
        
        // SMA values
        sma20Value.textContent = formatPrice(last.SMA_20 || '--', 2);
        sma50Value.textContent = formatPrice(last.SMA_50 || '--', 2);
        
        // Price range
        const range = parseFloat(last.High) - parseFloat(last.Low);
        priceRangeValue.textContent = formatPrice(range, 2);
        
        // Volume
        volumeValue.textContent = formatVolume(last.Volume);
    };
    
    // ======================
    // CHARTS
    // ======================
    const updateCharts = () => {
        if (!currentData || currentData.length === 0) return;
        
        // Use last 200 points for chart
        const chartData = currentData.slice(-200);
        const labels = chartData.map(row => row.Date);
        const prices = chartData.map(row => parseFloat(row.Close));
        const highs = chartData.map(row => parseFloat(row.High));
        const lows = chartData.map(row => parseFloat(row.Low));
        const opens = chartData.map(row => parseFloat(row.Open));
        
        // Price Chart
        updatePriceChart(labels, prices, opens, highs, lows);
        
        // RSI Chart
        updateRSIChart(labels, chartData);
        
        // MACD Chart
        updateMACDChart(labels, chartData);
    };
    
    const updatePriceChart = (labels, prices, opens, highs, lows) => {
        if (priceChart) priceChart.destroy();
        
        const chartType = chartTypeSelect.value;
        
        if (chartType === 'candlestick') {
            // Candlestick chart
            priceChart = new Chart(priceChartCanvas, {
                type: 'candlestick',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'قیمت',
                        data: chartData.map((row, i) => ({
                            x: labels[i],
                            o: opens[i],
                            h: highs[i],
                            l: lows[i],
                            c: prices[i]
                        }))
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { type: 'category' }, y: { beginAtZero: false } }
                }
            });
        } else if (chartType === 'bar') {
            priceChart = new Chart(priceChartCanvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'قیمت بسته',
                        data: prices,
                        backgroundColor: 'rgba(37, 99, 235, 0.5)',
                        borderColor: 'rgba(37, 99, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: true } },
                    scales: { y: { beginAtZero: false } }
                }
            });
        } else {
            // Line chart
            priceChart = new Chart(priceChartCanvas, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'قیمت بسته',
                            data: prices,
                            borderColor: 'rgb(37, 99, 235)',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            tension: 0.2,
                            fill: true,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: { 
                        legend: { display: true },
                        tooltip: {
                            callbacks: {
                                label: (context) => context.dataset.label + ': ' + formatPrice(context.raw)
                            }
                        }
                    },
                    scales: { y: { beginAtZero: false } }
                }
            });
        }
    };
    
    const updateRSIChart = (labels, data) => {
        if (rsiChart) rsiChart.destroy();
        
        const rsiValues = data.map(row => parseFloat(row.RSI));
        
        rsiChart = new Chart(rsiChartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'RSI',
                        data: rsiValues,
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.2,
                        fill: true,
                        pointRadius: 0
                    },
                    {
                        label: 'Overbought (70)',
                        data: labels.map(() => 70),
                        borderColor: 'rgb(239, 68, 68)',
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Oversold (30)',
                        data: labels.map(() => 30),
                        borderColor: 'rgb(16, 185, 129)',
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true } },
                scales: { y: { min: 0, max: 100 } }
            }
        });
    };
    
    const updateMACDChart = (labels, data) => {
        if (macdChart) macdChart.destroy();
        
        const macdValues = data.map(row => parseFloat(row.MACD));
        const signalValues = data.map(row => parseFloat(row.Signal));
        const histogramValues = data.map(row => parseFloat(row.Histogram));
        
        macdChart = new Chart(macdChartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'MACD',
                        data: macdValues,
                        borderColor: 'rgb(37, 99, 235)',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        tension: 0.2,
                        fill: true,
                        pointRadius: 0,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Signal',
                        data: signalValues,
                        borderColor: 'rgb(245, 158, 11)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.2,
                        fill: true,
                        pointRadius: 0,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Histogram',
                        data: histogramValues,
                        type: 'bar',
                        backgroundColor: histogramValues.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)'),
                        borderColor: histogramValues.map(v => v >= 0 ? 'rgb(16, 185, 129)' : 'rgb(239, 68, 68)'),
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true } },
                scales: {
                    y: { type: 'linear', position: 'left', title: { display: true, text: 'MACD' } },
                    y1: { type: 'linear', position: 'right', title: { display: true, text: 'Histogram' }, grid: { drawOnChartArea: false } }
                }
            }
        });
    };
    
    // ======================
    // DOWNLOAD HANDLERS
    // ======================
    const downloadFile = (type) => {
        if (!currentData || currentData.length === 0) {
            showStatus('هیچ داده‌ای برای دانلود وجود ندارد', true);
            return;
        }
        
        const url = `/api/download/${encodeURIComponent(currentSymbol)}/${type}`;
        window.open(url, '_blank');
        showStatus('فایل در حال دانلود است...');
    };
    
    // ======================
    // ANALYSIS HANDLERS
    // ======================
    const saveAnalysis = async () => {
        const text = analysisEditor.value.trim();
        if (!text) {
            showStatus('متن تحلیل خالی است', true);
            return;
        }
        
        if (!currentSymbol) {
            showStatus('هیچ سهمی انتخاب نشده است', true);
            return;
        }
        
        try {
            const response = await fetch('/api/analysis/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: currentSymbol, analysis: text })
            });
            
            const result = await response.json();
            if (result.success) {
                showStatus('تحلیل با موفقیت ذخیره شد: ' + result.filename);
            } else {
                showStatus('خطا در ذخیره: ' + result.error, true);
            }
        } catch (error) {
            showStatus('خطا در ذخیره تحلیل: ' + error.message, true);
        }
    };
    
    const postAnalysis = async () => {
        const text = analysisEditor.value.trim();
        if (!text) {
            showStatus('متن تحلیل خالی است', true);
            return;
        }
        
        // Copy to clipboard for sharing
        try {
            const shareText = `تحلیل ${currentSymbol}:\n\n${text}\n\n#${currentSymbol} #بازار_مالي #تحلیل`;
            await navigator.clipboard.writeText(shareText);
            showStatus('متن تحلیل در کلیپ‌بورد کپی شد - می‌توانید آن را به اشتراک بگذارید');
        } catch (error) {
            // Fallback for clipboard API
            showStatus('برای به اشتراک‌گذاری، متن را کپی کنید', true);
        }
    };
    
    // ======================
    // EVENT LISTENERS
    // ======================
    fetchBtn.addEventListener('click', fetchData);
    loadDataBtn.addEventListener('click', fetchData);
    saveBtn.addEventListener('click', saveAnalysis);
    postBtn.addEventListener('click', postAnalysis);
    
    downloadPrice.addEventListener('click', () => downloadFile('price'));
    downloadIndicators.addEventListener('click', () => downloadFile('indicators'));
    downloadFull.addEventListener('click', () => downloadFile('full'));
    
    chartTypeSelect.addEventListener('change', () => {
        if (currentData && currentData.length > 0) {
            updateCharts();
        }
    });
    
    // Toggle indicator buttons
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const ind = btn.dataset.ind;
            visibleIndicators[ind] = !visibleIndicators[ind];
            btn.classList.toggle('active', visibleIndicators[ind]);
            updateCharts();
        });
    });
    
    // Enter key in symbol input
    symbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') fetchData();
    });
    
    // ======================
    // INITIALIZATION
    // ======================
    loadSymbols();
    
    // Auto-fetch data after symbols load
    setTimeout(() => {
        if (symbolInput.value) {
            fetchData();
        }
    }, 500);
    
    console.log('Dashboard Ready!');
});