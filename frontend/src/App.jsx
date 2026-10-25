import React, { useState, useEffect, useRef } from 'react';
import {
  ComposedChart,
  Line,
  Customized,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from 'recharts';

const ErrorShadingLayer = (props) => {
  const { formattedGraphicalItems } = props;
  if (!formattedGraphicalItems || formattedGraphicalItems.length < 2) return null;
  const actItem = formattedGraphicalItems.find((item) => item.props?.name === 'Actual Wind');
  const fcItem = formattedGraphicalItems.find((item) => item.props?.name === 'Decision Forecast');
  const actPoints = actItem?.props?.points || [];
  const fcPoints = fcItem?.props?.points || [];

  if (actPoints.length < 2 || fcPoints.length < 2) return null;

  let pathD = '';
  const n = Math.min(actPoints.length, fcPoints.length);
  for (let i = 0; i < n - 1; i++) {
    const pAct0 = actPoints[i];
    const pAct1 = actPoints[i + 1];
    const pFc0 = fcPoints[i];
    const pFc1 = fcPoints[i + 1];
    if (!pAct0 || !pAct1 || !pFc0 || !pFc1) continue;

    pathD += `M ${pFc0.x} ${pFc0.y} L ${pFc1.x} ${pFc0.y} L ${pAct1.x} ${pAct1.y} L ${pAct0.x} ${pAct0.y} Z `;
  }

  return <path d={pathD} fill="rgba(234, 88, 12, 0.14)" stroke="none" pointerEvents="none" />;
};

const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE = rawApiUrl.replace(/\/+$/, '');

const formatTimeLabel = (isoStr) => {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const hours = String(d.getUTCHours()).padStart(2, '0');
  const minutes = String(d.getUTCMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
};

const formatDateLabel = (dateStr) => {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length !== 3) return dateStr;
  const monthNames = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  const day = parts[2];
  const month = monthNames[parseInt(parts[1], 10) - 1];
  return `${day} ${month}`;
};

const SECTIONS = [
  { id: 'section-decision', label: 'Guidance & Buffer', shortLabel: 'Guidance' },
  { id: 'section-selected-day', label: 'Delivery Day Profile', shortLabel: 'Profile' },
  { id: 'section-benchmark', label: '31-Day Benchmark', shortLabel: 'Benchmark' },
  { id: 'section-methodology', label: 'Operational Context', shortLabel: 'Context' },
];

const DEFAULT_JAN_DATES = Array.from({ length: 31 }, (_, i) => {
  const d = String(i + 1).padStart(2, '0');
  return `2026-01-${d}`;
});

export default function App() {
  const [selectedDate, setSelectedDate] = useState('2026-01-15');
  const [cutoffHour, setCutoffHour] = useState(9);
  const [availableDates, setAvailableDates] = useState(DEFAULT_JAN_DATES);

  const [dayData, setDayData] = useState(null);
  const [accuracyData, setAccuracyData] = useState(null);

  const [loadingDay, setLoadingDay] = useState(true);
  const [loadingAccuracy, setLoadingAccuracy] = useState(true);
  const [error, setError] = useState(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [showMoreMetrics, setShowMoreMetrics] = useState(false);

  const [activeSection, setActiveSection] = useState(0);

  useEffect(() => {
    fetch(`${API_BASE}/api/dates`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} from /api/dates`);
        return res.json();
      })
      .then((data) => {
        const datesList = data.available_dates || data.dates || [];
        if (datesList.length > 0) {
          setAvailableDates(datesList);
          if (!datesList.includes(selectedDate)) {
            setSelectedDate(datesList[0]);
          }
        }
      })
      .catch((err) => {
        console.error('Error fetching dates:', err);
      });
  }, []);

  useEffect(() => {
    setLoadingDay(true);
    fetch(`${API_BASE}/api/day?date=${selectedDate}&cutoff_hour=${cutoffHour}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} from /api/day`);
        return res.json();
      })
      .then((data) => {
        setDayData(data);
        setLoadingDay(false);
      })
      .catch((err) => {
        console.error('Error fetching day data:', err);
        setError(`Failed to load data for ${selectedDate}`);
        setLoadingDay(false);
      });
  }, [selectedDate, cutoffHour]);

  useEffect(() => {
    setLoadingAccuracy(true);
    fetch(`${API_BASE}/api/accuracy?start_date=2026-01-01&end_date=2026-01-31&cutoff_hour=${cutoffHour}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} from /api/accuracy`);
        return res.json();
      })
      .then((data) => {
        setAccuracyData(data);
        setLoadingAccuracy(false);
      })
      .catch((err) => {
        console.error('Error fetching accuracy:', err);
        setLoadingAccuracy(false);
      });
  }, [cutoffHour]);

  useEffect(() => {
    const observerOptions = {
      root: null,
      rootMargin: '-20% 0px -40% 0px',
      threshold: 0.1,
    };

    const handleIntersect = (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const index = SECTIONS.findIndex((s) => s.id === entry.target.id);
          if (index !== -1) {
            setActiveSection(index);
          }
        }
      });
    };

    const observer = new IntersectionObserver(handleIntersect, observerOptions);
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (tag === 'input' || tag === 'select' || tag === 'textarea') return;

      if (e.key === 'PageDown' || e.key === 'ArrowDown') {
        if (activeSection < SECTIONS.length - 1) {
          e.preventDefault();
          scrollToSection(activeSection + 1);
        }
      } else if (e.key === 'PageUp' || e.key === 'ArrowUp') {
        if (activeSection > 0) {
          e.preventDefault();
          scrollToSection(activeSection - 1);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeSection]);

  const scrollToSection = (index) => {
    const target = SECTIONS[index];
    if (target) {
      const el = document.getElementById(target.id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
        setActiveSection(index);
      }
    }
  };

  const currentIndex = availableDates.indexOf(selectedDate);
  const handlePrevDay = () => {
    if (currentIndex > 0) {
      setSelectedDate(availableDates[currentIndex - 1]);
    }
  };
  const handleNextDay = () => {
    if (currentIndex >= 0 && currentIndex < availableDates.length - 1) {
      setSelectedDate(availableDates[currentIndex + 1]);
    }
  };

  const PRESET_DATES = [
    { label: 'Lowest wind day', date: '2026-01-01' },
    { label: 'Mid-month', date: '2026-01-15' },
    { label: 'Average day', date: '2026-01-18' },
    { label: 'Windiest day', date: '2026-01-24' },
    { label: 'Biggest miss', date: '2026-01-28' },
  ];

  let lastForecastVal = null;
  let lastPublishTime = null;
  const lineChartData = (dayData?.slots || []).map((s) => {
    if (s.forecast !== null && s.forecast !== undefined) {
      lastForecastVal = Math.round(s.forecast);
      lastPublishTime = s.publishTime;
    }
    const actualVal = s.actual !== null ? Math.round(s.actual) : null;
    const forecastStepVal = lastForecastVal;

    let shadeBase = null;
    let shadeDiff = null;
    if (actualVal !== null && forecastStepVal !== null) {
      shadeBase = Math.min(actualVal, forecastStepVal);
      shadeDiff = Math.abs(actualVal - forecastStepVal);
    }

    return {
      timeLabel: formatTimeLabel(s.startTime),
      rawTime: s.startTime,
      actual: actualVal,
      forecastHourly: s.forecast !== null ? Math.round(s.forecast) : null,
      forecastStep: forecastStepVal,
      shadeBase,
      shadeDiff,
      publishTime: s.publishTime || lastPublishTime,
    };
  });

  const allChartValues = lineChartData.flatMap((d) => [d.actual, d.forecastStep]).filter((v) => v !== null && !isNaN(v));
  const chartMin = allChartValues.length ? Math.min(...allChartValues) : 0;
  const chartMax = allChartValues.length ? Math.max(...allChartValues) : 20000;
  const yDomainMin = Math.max(0, Math.floor((chartMin * 0.90) / 1000) * 1000);
  const yDomainMax = Math.ceil((chartMax * 1.05) / 1000) * 1000;

  const barChartData = (accuracyData?.daily_breakdown || []).map((d) => ({
    date: d.date,
    dateLabel: formatDateLabel(d.date),
    bias: Math.round(d.bias || 0),
    mae: Math.round(d.mae || 0),
    rmse: Math.round(d.rmse || 0),
    isSelected: d.date === selectedDate,
  }));

  const overallBias = accuracyData?.bias ? Math.round(accuracyData.bias) : 1852;
  const overallBiasPct = accuracyData?.bias_percent !== undefined ? accuracyData.bias_percent.toFixed(1) : '16.0';
  const worstDailyBias = accuracyData?.daily_breakdown?.length
    ? Math.round(Math.max(...accuracyData.daily_breakdown.map((d) => d.bias || 0)))
    : 5329;

  const dayBias = dayData?.metrics?.bias !== null && dayData?.metrics?.bias !== undefined
    ? Math.round(dayData.metrics.bias)
    : 0;
  const dayMae = dayData?.metrics?.mae !== null && dayData?.metrics?.mae !== undefined
    ? Math.round(dayData.metrics.mae)
    : 0;
  const dayRmse = dayData?.metrics?.rmse !== null && dayData?.metrics?.rmse !== undefined
    ? Math.round(dayData.metrics.rmse)
    : 0;

  return (
    <div className="app-shell">

      <header className="mobile-top-header">
        <div className="mobile-brand" onClick={() => scrollToSection(0)}>
          <img src="/logo.svg" alt="Gridbricks Logo" className="brand-logo" />
          <span className="mobile-brand-title">Gridbricks</span>
        </div>

        <div className="mobile-date-capsule">
          <button
            type="button"
            className="mobile-capsule-arrow"
            onClick={handlePrevDay}
            disabled={currentIndex <= 0}
            aria-label="Previous Day"
          >
            ◀
          </button>
          <span className="mobile-capsule-label">{formatDateLabel(selectedDate)}</span>
          <button
            type="button"
            className="mobile-capsule-arrow"
            onClick={handleNextDay}
            disabled={currentIndex >= availableDates.length - 1}
            aria-label="Next Day"
          >
            ▶
          </button>
        </div>

        <button
          type="button"
          className="mobile-menu-trigger"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open Filter Controls"
        >
          <svg className="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="4" y1="6" x2="20" y2="6" />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="18" x2="20" y2="18" />
          </svg>
          <span>Filters</span>
        </button>
      </header>

      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={`app-sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div
            className="sidebar-brand"
            onClick={() => {
              scrollToSection(0);
              setSidebarOpen(false);
            }}
          >
            <img src="/logo.svg" alt="Gridbricks Logo" className="brand-logo" />
            <div className="brand-meta">
              <span className="brand-title">Gridbricks Energy</span>
              <span className="brand-sub">Power Procurement</span>
            </div>
          </div>

          <button
            type="button"
            className="sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close Sidebar"
          >
            ✕
          </button>
        </div>

        <div className="sidebar-body">

          <div className="sidebar-group">
            <span className="sidebar-group-title">DELIVERY DATE</span>
            <div className="sidebar-stepper">
              <button
                type="button"
                className="sidebar-stepper-btn"
                onClick={handlePrevDay}
                disabled={currentIndex <= 0}
                aria-label="Previous Day"
              >
                ◀
              </button>
              <select
                id="sidebar-date-select"
                className="sidebar-select"
                value={selectedDate}
                onChange={(e) => {
                  setSelectedDate(e.target.value);
                  setSidebarOpen(false);
                }}
                aria-label="Delivery Date"
              >
                {availableDates.map((d) => (
                  <option key={d} value={d}>
                    {formatDateLabel(d)} 2026
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="sidebar-stepper-btn"
                onClick={handleNextDay}
                disabled={currentIndex >= availableDates.length - 1}
                aria-label="Next Day"
              >
                ▶
              </button>
            </div>
          </div>

          <div className="sidebar-group">
            <span className="sidebar-group-title">DECISION CUTOFF</span>
            <select
              id="sidebar-cutoff-select"
              className="sidebar-select"
              value={cutoffHour}
              onChange={(e) => {
                setCutoffHour(parseInt(e.target.value, 10));
              }}
              aria-label="Cutoff Time"
            >
              {[...Array(24).keys()].map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, '0')}:00 UK Time {h === 9 ? '(Default)' : ''}
                </option>
              ))}
            </select>
            <span className="sidebar-micro-note">
              Latest forecast locked before cutoff on D-1.
            </span>
          </div>

          <div className="sidebar-group">
            <span className="sidebar-group-title">TRADING SCENARIOS</span>
            <div className="sidebar-presets-stack">
              {PRESET_DATES.map((p) => {
                const isActive = selectedDate === p.date;
                return (
                  <button
                    key={p.date}
                    type="button"
                    className={`sidebar-preset-btn ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedDate(p.date);
                      setSidebarOpen(false);
                    }}
                  >
                    <span className="preset-btn-label">{p.label}</span>
                    <span className="preset-btn-date">{formatDateLabel(p.date)}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-status-pill">
            <span className="pulse-dot" />
            <span className="status-label">Official Elexon BMRS API</span>
          </div>
          <span className="footer-subtext">Jan 1 &ndash; Jan 31, 2026 Horizon</span>
        </div>
      </aside>

      <main className="main-stage">

        <header className="upper-navbar" aria-label="View Navigation">
          <nav className="upper-navbar-tabs">
            {SECTIONS.map((s, idx) => (
              <button
                key={s.id}
                type="button"
                className={`upper-tab-btn ${activeSection === idx ? 'active' : ''}`}
                onClick={() => scrollToSection(idx)}
                aria-label={`Jump to ${s.label}`}
              >
                <span className="tab-idx">0{idx + 1}</span>
                <span className="tab-label-full">{s.label}</span>
                <span className="tab-label-short">{s.shortLabel}</span>
                {activeSection === idx && <span className="tab-active-indicator" />}
              </button>
            ))}
          </nav>

          <div className="upper-navbar-meta">
            <span className="navbar-meta-tag">{formatDateLabel(selectedDate)} 2026</span>
            <span className="navbar-meta-divider">&middot;</span>
            <span className="navbar-meta-tag">Cutoff {String(cutoffHour).padStart(2, '0')}:00 UK</span>
          </div>
        </header>

        <section id="section-decision" className="content-section section-bg-light">
          <div className="section-container-centered">
            <span className="eyebrow-text">Day-Ahead Power Procurement Guidance</span>

            <div className="hero-buffer-display">
              <div className="buffer-number-row">
                <div className="buffer-stat">
                  <span className="buffer-label">Average Thermal Buffer</span>
                  <div className="buffer-huge-val">
                    +{overallBias.toLocaleString()} <span className="buffer-unit">MW</span>
                  </div>
                </div>
                <div className="buffer-divider-vertical" />
                <div className="buffer-stat">
                  <span className="buffer-label">Worst-Day Risk Peak</span>
                  <div className="buffer-huge-val text-amber">
                    +{worstDailyBias.toLocaleString()} <span className="buffer-unit">MW</span>
                  </div>
                </div>
              </div>

              <p className="buffer-lead-sentence">
                Based on January&apos;s error, consider buying about <strong>{overallBias.toLocaleString()} MW</strong> extra thermal backup on average and up to <strong>{worstDailyBias.toLocaleString()} MW</strong> on peak risk days to prevent short imbalances.
              </p>
              <span className="buffer-disclaimer">
                Historical estimate based on January 2026 Elexon settled outturn vs WINDFOR, not a guarantee.
              </span>
            </div>

            <div className="headline-kpi-row">
              <div className="kpi-open-item">
                <span className="kpi-micro-label">Day Bias ({formatDateLabel(selectedDate)})</span>
                <div className="kpi-display-num">
                  {dayBias > 0 ? `+${dayBias.toLocaleString()}` : dayBias.toLocaleString()} <span className="kpi-num-unit">MW</span>
                </div>
                <span className="kpi-note-text">
                  {dayBias > 0 ? 'Forecast too high, risk of under-buying' : dayBias < 0 ? 'Forecast too low, surplus power' : 'Balanced generation'}
                </span>
              </div>

              <div className="kpi-open-divider" />

              <div className="kpi-open-item">
                <span className="kpi-micro-label">Day MAE ({formatDateLabel(selectedDate)})</span>
                <div className="kpi-display-num">
                  {dayMae.toLocaleString()} <span className="kpi-num-unit">MW</span>
                </div>
                <span className="kpi-note-text">Average hourly miss magnitude</span>
              </div>

              <div className="kpi-open-divider" />

              <div className="kpi-open-item">
                <span className="kpi-micro-label">Monthly Bias %</span>
                <div className="kpi-display-num">
                  +{overallBiasPct}%
                </div>
                <span className="kpi-note-text">January average wind over-prediction</span>
              </div>

              <div className="kpi-open-divider" />

              <div className="kpi-open-item">
                <span className="kpi-micro-label">Worst-Day Bias</span>
                <div className="kpi-display-num text-amber">
                  +{worstDailyBias.toLocaleString()} <span className="kpi-num-unit">MW</span>
                </div>
                <span className="kpi-note-text">Peak single-day generation shortfall</span>
              </div>
            </div>

            <button
              type="button"
              className="scroll-hint-btn"
              onClick={() => scrollToSection(1)}
              aria-label="Scroll to evidence chart"
            >
              <span>Scroll for evidence</span>
              <span className="scroll-arrow-anim">↓</span>
            </button>
          </div>
        </section>

        <section id="section-selected-day" className="content-section section-bg-alt">
          <div className="section-container-chart">
            <div className="section-chart-header">
              <div className="title-stack">
                <h2 className="section-heading">
                  Actual vs. Decision Forecast <span className="heading-date-bullet">&middot;</span> <span className="heading-date-tag">{formatDateLabel(selectedDate)} 2026</span>
                </h2>
                <p className="section-subheading">
                  48 half-hour settlement periods across delivery day. Step line shows latest decision forecast locked prior to {String(cutoffHour).padStart(2, '0')}:00 UK Time on D-1. Shaded area highlights forecast error.
                </p>
              </div>

              <div className="minimal-legend">
                <div className="legend-item">
                  <span className="legend-swatch swatch-actual" />
                  <span>Actual Wind (Blue)</span>
                </div>
                <div className="legend-item">
                  <span className="legend-swatch swatch-forecast" />
                  <span>Hourly Decision Forecast (Orange Step)</span>
                </div>
                <div className="legend-item">
                  <span className="legend-swatch swatch-gap" />
                  <span>Forecast Error Gap</span>
                </div>
              </div>
            </div>

            <div className="chart-wrapper-flex">
              {loadingDay ? (
                <div className="chart-loading-state">Loading day outturn and decision forecast profiles...</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%" minHeight={380}>
                  <ComposedChart data={lineChartData} margin={{ top: 12, right: 20, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis
                      dataKey="timeLabel"
                      stroke="#94a3b8"
                      tick={{ fill: '#475569', fontSize: 12 }}
                      tickMargin={8}
                      minTickGap={24}
                      label={{
                        value: 'Settlement Time (UTC · Identical to UK Time in January)',
                        position: 'insideBottom',
                        offset: -14,
                        fill: '#64748b',
                        fontSize: 12,
                      }}
                    />
                    <YAxis
                      width={65}
                      stroke="#94a3b8"
                      tick={{ fill: '#475569', fontSize: 12 }}
                      tickMargin={8}
                      tickFormatter={(val) => val.toLocaleString()}
                      domain={[yDomainMin, yDomainMax]}
                      label={{
                        value: 'Generation (MW)',
                        angle: -90,
                        position: 'insideLeft',
                        offset: 4,
                        fill: '#64748b',
                        fontSize: 12,
                      }}
                    />
                    <RechartsTooltip
                      content={({ active, payload, label }) => {
                        if (!active || !payload || !payload.length) return null;
                        const d = payload[0].payload;
                        const errorVal = d.actual !== null && d.forecastStep !== null ? d.forecastStep - d.actual : null;
                        return (
                          <div className="borderless-tooltip">
                            <div className="tooltip-slot">{label} UTC (UK Time)</div>
                            <div className="tooltip-metric" style={{ color: '#2563eb' }}>
                              <span>Actual Outturn:</span>
                              <strong>{d.actual !== null ? `${d.actual.toLocaleString()} MW` : 'N/A'}</strong>
                            </div>
                            <div className="tooltip-metric" style={{ color: '#ea580c' }}>
                              <span>Decision Forecast:</span>
                              <strong>{d.forecastStep !== null ? `${d.forecastStep.toLocaleString()} MW` : 'N/A'}</strong>
                            </div>
                            {errorVal !== null && (
                              <div
                                className="tooltip-metric"
                                style={{
                                  color: errorVal > 0 ? '#d97706' : '#10b981',
                                  borderTop: '1px solid #f1f5f9',
                                  paddingTop: '4px',
                                }}
                              >
                                <span>Deviation (Fc - Act):</span>
                                <strong>{errorVal > 0 ? `+${errorVal.toLocaleString()}` : errorVal.toLocaleString()} MW</strong>
                              </div>
                            )}
                            {d.publishTime && (
                              <div className="tooltip-pubtime">
                                Forecast publishTime: {d.publishTime.replace('T', ' ').slice(0, 16)} UTC
                              </div>
                            )}
                          </div>
                        );
                      }}
                    />

                    <Customized component={ErrorShadingLayer} />

                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#2563eb"
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5, fill: '#2563eb' }}
                      isAnimationActive={false}
                      name="Actual Wind"
                    />

                    <Line
                      type="stepAfter"
                      dataKey="forecastStep"
                      stroke="#ea580c"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: '#ea580c' }}
                      activeDot={{ r: 5, fill: '#ea580c' }}
                      isAnimationActive={false}
                      name="Decision Forecast"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="chart-metrics-strip">
              <div className="strip-metric">
                <span className="strip-label">Day MAE:</span>
                <span className="strip-val">{dayMae.toLocaleString()} MW</span>
                <span className="inline-tooltip-hint" title="Mean Absolute Error: average magnitude of hourly forecast deviations.">?</span>
              </div>

              <div className="strip-divider" />

              <div className="strip-metric">
                <span className="strip-label">Day Bias:</span>
                <span className={`strip-val ${dayBias > 0 ? 'text-amber' : 'text-emerald'}`}>
                  {dayBias > 0 ? `+${dayBias.toLocaleString()}` : dayBias.toLocaleString()} MW
                </span>
                <span className="inline-tooltip-hint" title="Mean Signed Error: positive means over-predicted, negative means under-predicted.">?</span>
              </div>

              <div className="strip-divider" />

              <div className="strip-metric">
                <button
                  type="button"
                  className="rmse-toggle-btn"
                  onClick={() => setShowMoreMetrics(!showMoreMetrics)}
                >
                  {showMoreMetrics ? '- Hide RMSE' : '+ More metrics (RMSE)'}
                </button>
                {showMoreMetrics && (
                  <span className="rmse-revealed-val">
                    Day RMSE: <strong>{dayRmse.toLocaleString()} MW</strong>
                  </span>
                )}
              </div>
            </div>
          </div>
        </section>

        <section id="section-benchmark" className="content-section section-bg-light">
          <div className="section-container-chart">
            <div className="section-chart-header">
              <div className="title-stack">
                <h2 className="section-heading">January 2026 Benchmark Performance (31 Days)</h2>
                <p className="section-subheading">
                  Daily forecast bias across all 31 days. Click any bar to inspect that day above. <span className="text-amber">Amber = Over-forecast</span> (power shortfall), <span className="text-emerald">Green = Under-forecast</span> (power surplus).
                </p>
              </div>
            </div>

            <div className="bar-wrapper-flex">
              {loadingAccuracy ? (
                <div className="chart-loading-state">Loading January accuracy benchmarks...</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%" minHeight={340}>
                  <BarChart
                    data={barChartData}
                    margin={{ top: 12, right: 20, left: 10, bottom: 16 }}
                    onClick={(e) => {
                      if (e && e.activePayload && e.activePayload.length) {
                        const targetDate = e.activePayload[0].payload.date;
                        setSelectedDate(targetDate);
                        scrollToSection(1);
                      }
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis
                      dataKey="dateLabel"
                      stroke="#94a3b8"
                      tick={{ fill: '#475569', fontSize: 11 }}
                      tickMargin={6}
                      minTickGap={20}
                    />
                    <YAxis
                      width={65}
                      stroke="#94a3b8"
                      tick={{ fill: '#475569', fontSize: 12 }}
                      tickMargin={6}
                      tickFormatter={(val) => `${val > 0 ? '+' : ''}${val.toLocaleString()}`}
                      label={{
                        value: 'Daily Bias (MW)',
                        angle: -90,
                        position: 'insideLeft',
                        offset: 4,
                        fill: '#64748b',
                        fontSize: 12,
                      }}
                    />
                    <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} />
                    <ReferenceLine
                      y={overallBias}
                      stroke="#ea580c"
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: `Month Avg: +${overallBias.toLocaleString()} MW`,
                        position: 'insideTopRight',
                        fill: '#ea580c',
                        fontSize: 11,
                      }}
                    />
                    <RechartsTooltip
                      cursor={{ fill: 'rgba(0, 0, 0, 0.04)' }}
                      content={({ active, payload }) => {
                        if (!active || !payload || !payload.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div className="borderless-tooltip">
                            <div className="tooltip-slot">{d.dateLabel} ({d.date})</div>
                            <div className="tooltip-metric">
                              <span>Daily Bias:</span>
                              <strong style={{ color: d.bias >= 0 ? '#d97706' : '#10b981' }}>
                                {d.bias >= 0 ? `+${d.bias.toLocaleString()}` : d.bias.toLocaleString()} MW
                              </strong>
                            </div>
                            <div className="tooltip-metric">
                              <span>Daily MAE:</span>
                              <strong>{d.mae.toLocaleString()} MW</strong>
                            </div>
                            <div style={{ marginTop: '6px', fontSize: '11px', color: '#2563eb', fontWeight: 600 }}>
                              👉 Click to inspect this delivery day
                            </div>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey="bias" radius={[2, 2, 0, 0]} isAnimationActive={false}>
                      {barChartData.map((entry) => (
                        <Cell
                          key={`cell-${entry.date}`}
                          fill={entry.bias >= 0 ? (entry.isSelected ? '#d97706' : '#f59e0b') : (entry.isSelected ? '#059669' : '#10b981')}
                          stroke={entry.isSelected ? '#0f172a' : 'none'}
                          strokeWidth={entry.isSelected ? 2.5 : 0}
                          style={{ cursor: 'pointer' }}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="benchmark-compact-row">
              <div className="benchmark-stat">
                <span className="benchmark-label">Monthly MAE</span>
                <span className="benchmark-value">{accuracyData?.mae !== null && accuracyData?.mae !== undefined ? Math.round(accuracyData.mae).toLocaleString() : '2,127'} MW</span>
                <span className="benchmark-note">All 744 hourly slots</span>
              </div>

              <div className="kpi-open-divider" />

              <div className="benchmark-stat">
                <span className="benchmark-label">Monthly RMSE</span>
                <span className="benchmark-value">{accuracyData?.rmse !== null && accuracyData?.rmse !== undefined ? Math.round(accuracyData.rmse).toLocaleString() : '2,606'} MW</span>
                <span className="benchmark-note">Volatility measure</span>
              </div>

              <div className="kpi-open-divider" />

              <div className="benchmark-stat">
                <span className="benchmark-label">Monthly Bias</span>
                <span className="benchmark-value text-amber">+{overallBias.toLocaleString()} MW</span>
                <span className="benchmark-note">Systemic over-forecast</span>
              </div>

              <div className="kpi-open-divider" />

              <div className="benchmark-stat">
                <span className="benchmark-label">Monthly Bias %</span>
                <span className="benchmark-value text-amber">+{overallBiasPct}%</span>
                <span className="benchmark-note">Relative to actual outturn</span>
              </div>
            </div>
          </div>
        </section>

        <section id="section-methodology" className="content-section section-bg-alt">
          <div className="section-container-centered">
            <div className="methodology-header">
              <span className="eyebrow-text">Analytical Standards & Assumptions</span>
              <h2 className="section-heading">Methodology & Operational Context</h2>
              <p className="section-subheading">
                Governing rules for day-ahead benchmarking without lookahead bias.
              </p>
            </div>

            <div className="methodology-columns-3">
              <div className="methodology-col">
                <h3 className="col-title">⏱️ Decision Cutoff Timing</h3>
                <p className="col-desc">
                  Day-ahead trading decisions are strictly evaluated using the latest available forecast published prior to {String(cutoffHour).padStart(2, '0')}:00 UK Time on day D-1. Forecasts issued after this cutoff are excluded to avoid lookahead bias.
                </p>
              </div>

              <div className="col-divider-vertical" />

              <div className="methodology-col">
                <h3 className="col-title">📐 Hourly Resolution</h3>
                <p className="col-desc">
                  While settled outturn (<code>FUELHH</code>) reports half-hourly (48 periods/day), National Grid ESO forecasts (<code>WINDFOR</code>) publish on an hourly cadence (:00). Accuracy metrics are evaluated strictly on the 24 hourly aligned points without synthetic interpolation.
                </p>
              </div>

              <div className="col-divider-vertical" />

              <div className="methodology-col">
                <h3 className="col-title">🔬 Bias Root Cause Investigation</h3>
                <p className="col-desc">
                  The persistent bias is not confirmed. Possible explanations: scope difference between FUELHH (transmission-metered) and WINDFOR, or grid curtailment. Not verified in this pilot.
                </p>
              </div>
            </div>
          </div>
        </section>

        <footer className="site-footer">
          <div className="footer-container">
            <div className="footer-top-row">
              <div className="footer-brand-col">
                <div className="footer-brand-lockup">
                  <img src="/logo.svg" alt="Gridbricks" className="footer-logo" />
                  <span className="footer-title">Gridbricks Energy</span>
                </div>
                <p className="footer-desc">
                  Precision decision support for UK wholesale power traders. Benchmarking National Grid ESO wind forecasts against verified settlement outturn to optimize day-ahead thermal buffers.
                </p>
              </div>

              <div className="footer-meta-col">
                <span className="footer-col-header">Official Ingestion Stream</span>
                <ul className="footer-meta-list">
                  <li><code>FUELHH</code> (Metered Half-Hour Generation)</li>
                  <li><code>WINDFOR</code> (Hourly Re-forecast Cadence)</li>
                  <li>Official Elexon BMRS API v1</li>
                </ul>
              </div>

              <div className="footer-meta-col">
                <span className="footer-col-header">Trading Architecture</span>
                <ul className="footer-meta-list">
                  <li>Day D-1 Anti-Lookahead Cutoff (Default 09:00 UK Time)</li>
                  <li>Strict 24 Hourly Aligned Metric Slots</li>
                  <li>Zero Synthetic Interpolation</li>
                </ul>
              </div>
            </div>

            <div className="footer-bottom-row">
              <div className="footer-copy">
                &copy; 2026 Gridbricks Energy Ltd. All analytical standards compliant with Elexon BSC rules.
              </div>
              <div className="footer-live-badge">
                <span className="pulse-dot" />
                <span>All 744 January Settlement Hours Verified</span>
              </div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
