const { useState, useEffect, useRef, useMemo, useCallback } = React;

// Configuration
const API_KEY = 'JIKDWX97Y7CHIJQ2';
const BASE_URL = 'https://www.alphavantage.co/query';

// --- API Utilities ---
const fetchSearch = async (query) => {
    if (!query) return [];
    try {
        const res = await fetch(`${BASE_URL}?function=SYMBOL_SEARCH&keywords=${query}&apikey=${API_KEY}`);
        const data = await res.json();
        return data.bestMatches || [];
    } catch (e) {
        console.error("Search API Error:", e);
        return [];
    }
};

const fetchQuote = async (symbol) => {
    try {
        const res = await fetch(`${BASE_URL}?function=GLOBAL_QUOTE&symbol=${symbol}&apikey=${API_KEY}`);
        const data = await res.json();
        return data['Global Quote'] || null;
    } catch (e) {
        console.error("Quote API Error:", e);
        return null;
    }
};

const fetchTimeSeries = async (symbol) => {
    try {
        const res = await fetch(`${BASE_URL}?function=TIME_SERIES_DAILY&symbol=${symbol}&apikey=${API_KEY}`);
        const data = await res.json();
        return data['Time Series (Daily)'] || null;
    } catch (e) {
        console.error("Time Series API Error:", e);
        return null;
    }
};

const fetchNews = async (symbol) => {
    try {
        const res = await fetch(`${BASE_URL}?function=NEWS_SENTIMENT&tickers=${symbol}&limit=10&apikey=${API_KEY}`);
        const data = await res.json();
        return data.feed || [];
    } catch (e) {
        console.error("News API Error:", e);
        return [];
    }
};

// --- Components ---

const SearchModal = ({ isOpen, onClose, favorites, toggleFavorite }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!isOpen) {
            setQuery('');
            setResults([]);
        }
    }, [isOpen]);

    useEffect(() => {
        const timer = setTimeout(async () => {
            if (query.trim().length > 0) {
                setLoading(true);
                const data = await fetchSearch(query);
                setResults(data);
                setLoading(false);
            } else {
                setResults([]);
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [query]);

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">종목 검색</h2>
                    <button className="close-btn" onClick={onClose}>
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>
                <div className="modal-body">
                    <div className="search-input-wrapper">
                        <span className="material-symbols-outlined">search</span>
                        <input 
                            type="text" 
                            className="search-input" 
                            placeholder="종목명 또는 티커(Ticker) 검색..." 
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            autoFocus
                        />
                    </div>
                    
                    {loading ? (
                        <div className="spinner"></div>
                    ) : (
                        <div className="search-results">
                            {results.map((item) => {
                                const symbol = item['1. symbol'];
                                const name = item['2. name'];
                                const isChecked = favorites.some(f => f.symbol === symbol);
                                
                                return (
                                    <div key={symbol} className="search-result-item" onClick={() => toggleFavorite({symbol, name})}>
                                        <input 
                                            type="checkbox" 
                                            className="custom-checkbox"
                                            checked={isChecked}
                                            readOnly
                                        />
                                        <div className="search-result-info">
                                            <div className="search-result-symbol">{symbol}</div>
                                            <div className="search-result-name">{name}</div>
                                        </div>
                                    </div>
                                );
                            })}
                            {!loading && query && results.length === 0 && (
                                <div className="empty-state">검색 결과가 없습니다.</div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const FavoriteCard = ({ favorite, isActive, onClick, onToggle }) => {
    const [quote, setQuote] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadQuote = async () => {
            setLoading(true);
            const data = await fetchQuote(favorite.symbol);
            if (data && data['05. price']) {
                setQuote(data);
            }
            setLoading(false);
        };
        loadQuote();
        // 실제로는 주기적 폴링(polling)을 넣을 수 있지만, API 제한상 1회만 호출
    }, [favorite.symbol]);

    const price = quote ? parseFloat(quote['05. price']).toFixed(2) : '---';
    const change = quote ? parseFloat(quote['09. change']) : 0;
    const changePercent = quote ? quote['10. change percent'] : '---';
    const isPositive = change > 0;
    const isNegative = change < 0;

    return (
        <div className={`glass-panel favorite-card ${isActive ? 'active' : ''}`} onClick={() => onClick(favorite)}>
            <div className="card-header">
                <div className="card-symbol" onClick={e => e.stopPropagation()}>
                    <input 
                        type="checkbox" 
                        className="custom-checkbox"
                        checked={true}
                        onChange={() => onToggle(favorite)}
                    />
                    {favorite.symbol}
                </div>
            </div>
            {loading ? (
                <div style={{height: '40px', display:'flex', alignItems:'center'}}>
                    <div className="spinner" style={{width:'20px', height:'20px', margin:0, borderWidth:'2px'}}></div>
                </div>
            ) : (
                <>
                    <div className="card-price">${price}</div>
                    <div className={`card-change ${isPositive ? 'text-success' : isNegative ? 'text-danger' : 'text-neutral'}`}>
                        <span className="material-symbols-outlined" style={{fontSize: '1rem'}}>
                            {isPositive ? 'trending_up' : isNegative ? 'trending_down' : 'remove'}
                        </span>
                        {change > 0 ? '+' : ''}{change.toFixed(2)} ({changePercent})
                    </div>
                </>
            )}
        </div>
    );
};

const ChartSection = ({ activeStock }) => {
    const chartRef = useRef(null);
    const chartInstance = useRef(null);
    const [timeframe, setTimeframe] = useState('1M');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!activeStock) return;
        
        const loadData = async () => {
            setLoading(true);
            const tsData = await fetchTimeSeries(activeStock.symbol);
            if (tsData) {
                // Convert object to array and sort chronologically
                const entries = Object.entries(tsData)
                    .map(([date, values]) => ({
                        date,
                        close: parseFloat(values['4. close'])
                    }))
                    .sort((a, b) => new Date(a.date) - new Date(b.date));
                setData(entries);
            } else {
                setData([]);
            }
            setLoading(false);
        };
        
        loadData();
    }, [activeStock]);

    useEffect(() => {
        if (!data || !chartRef.current) return;

        let filteredData = [...data];
        const now = new Date(data[data.length - 1]?.date || Date.now()); // use last data point date
        
        if (timeframe === '1W') {
            const weekAgo = new Date(now);
            weekAgo.setDate(weekAgo.getDate() - 7);
            filteredData = data.filter(d => new Date(d.date) >= weekAgo);
        } else if (timeframe === '1M') {
            const monthAgo = new Date(now);
            monthAgo.setMonth(monthAgo.getMonth() - 1);
            filteredData = data.filter(d => new Date(d.date) >= monthAgo);
        } else if (timeframe === '3M') {
            const threeMonthsAgo = new Date(now);
            threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
            filteredData = data.filter(d => new Date(d.date) >= threeMonthsAgo);
        }

        const labels = filteredData.map(d => d.date);
        const values = filteredData.map(d => d.close);
        
        const isPositive = values[values.length - 1] >= values[0];
        const lineColor = isPositive ? '#10b981' : '#ef4444';
        const gradientColor = isPositive ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';

        if (chartInstance.current) {
            chartInstance.current.destroy();
        }

        const ctx = chartRef.current.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, gradientColor);
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

        chartInstance.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: `${activeStock.symbol} Price`,
                    data: values,
                    borderColor: lineColor,
                    backgroundColor: gradient,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(30, 41, 59, 0.9)',
                        titleColor: '#f8fafc',
                        bodyColor: '#f8fafc',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `$${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { maxTicksLimit: 6, color: '#94a3b8' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8', callback: (val) => `$${val}` }
                    }
                }
            }
        });
        
    }, [data, timeframe]);

    if (!activeStock) {
        return (
            <div className="glass-panel chart-section" style={{display:'flex', alignItems:'center', justifyContent:'center', height:'400px'}}>
                <div className="empty-state">
                    <span className="material-symbols-outlined">show_chart</span>
                    <p>종목을 선택하면 차트가 표시됩니다.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel chart-section">
            <div className="chart-header">
                <div className="chart-title">{activeStock.name} ({activeStock.symbol})</div>
                <div className="timeframe-selector">
                    {['1W', '1M', '3M', '1Y'].map(tf => (
                        <button 
                            key={tf}
                            className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
                            onClick={() => setTimeframe(tf)}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>
            {loading ? (
                <div className="spinner"></div>
            ) : (
                <div className="chart-container">
                    <canvas ref={chartRef}></canvas>
                </div>
            )}
        </div>
    );
};

const NewsSection = ({ activeStock }) => {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!activeStock) return;
        
        const loadNews = async () => {
            setLoading(true);
            const data = await fetchNews(activeStock.symbol);
            // Limit to 10
            setNews((data || []).slice(0, 10));
            setLoading(false);
        };
        
        loadNews();
    }, [activeStock]);

    if (!activeStock) return null;

    return (
        <div className="news-section">
            <h2 className="news-header">
                <span className="material-symbols-outlined">article</span>
                관련 최신 뉴스
            </h2>
            {loading ? (
                <div className="spinner"></div>
            ) : news.length === 0 ? (
                <div className="empty-state">관련 뉴스가 없습니다.</div>
            ) : (
                <div className="news-grid">
                    {news.map((item, idx) => (
                        <div key={idx} className="news-card">
                            <div className="news-source">{item.source}</div>
                            <h3 className="news-title">{item.title}</h3>
                            <p className="news-summary">{item.summary}</p>
                            <div className="news-footer">
                                <span>{new Date(item.time_published.replace(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})/, '$1-$2-$3T$4:$5:$6')).toLocaleDateString()}</span>
                                <a href={item.url} target="_blank" rel="noopener noreferrer" className="news-link">
                                    원문 보기
                                    <span className="material-symbols-outlined" style={{fontSize: '1rem'}}>open_in_new</span>
                                </a>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const App = () => {
    // Initial default mock favorite just to show UI if needed, but we start empty per req.
    // Or we can provide Apple as default. Let's start with Apple (AAPL) for demo purposes if empty.
    const [favorites, setFavorites] = useState([
        { symbol: 'AAPL', name: 'Apple Inc' }
    ]);
    const [activeStock, setActiveStock] = useState(favorites[0]);
    const [isSearchOpen, setIsSearchOpen] = useState(false);

    const toggleFavorite = (stock) => {
        setFavorites(prev => {
            const exists = prev.some(f => f.symbol === stock.symbol);
            if (exists) {
                const newFavs = prev.filter(f => f.symbol !== stock.symbol);
                if (activeStock?.symbol === stock.symbol) {
                    setActiveStock(newFavs.length > 0 ? newFavs[0] : null);
                }
                return newFavs;
            } else {
                if (prev.length >= 7) {
                    alert("즐겨찾기는 최대 7개까지만 추가할 수 있습니다.");
                    return prev;
                }
                // If it's the first favorite added, make it active
                if (prev.length === 0) {
                    setActiveStock(stock);
                }
                return [...prev, stock];
            }
        });
    };

    return (
        <div className="container">
            <header className="header">
                <h1>
                    <span className="material-symbols-outlined" style={{fontSize: '2.5rem', color: 'var(--accent-color)'}}>monitoring</span>
                    MarketPulse
                </h1>
                <button className="btn" onClick={() => setIsSearchOpen(true)}>
                    <span className="material-symbols-outlined">star</span>
                    즐겨찾기
                </button>
            </header>

            {favorites.length > 0 ? (
                <div className="favorites-container">
                    {favorites.map(fav => (
                        <FavoriteCard 
                            key={fav.symbol} 
                            favorite={fav} 
                            isActive={activeStock?.symbol === fav.symbol}
                            onClick={setActiveStock}
                            onToggle={toggleFavorite}
                        />
                    ))}
                </div>
            ) : (
                <div className="glass-panel" style={{padding: '2rem', textAlign: 'center', marginBottom: '2rem', color: 'var(--text-muted)'}}>
                    즐겨찾기된 종목이 없습니다. 우측 상단의 '즐겨찾기' 버튼을 눌러 추가해주세요.
                </div>
            )}

            <div className="main-grid">
                <ChartSection activeStock={activeStock} />
                <NewsSection activeStock={activeStock} />
            </div>

            <SearchModal 
                isOpen={isSearchOpen} 
                onClose={() => setIsSearchOpen(false)} 
                favorites={favorites}
                toggleFavorite={toggleFavorite}
            />
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
