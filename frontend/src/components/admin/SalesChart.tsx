import React, { useState, useMemo } from 'react';
import type { SalesOverTimePoint } from '../../types/admin';
import { TrendingUp, Calendar } from 'lucide-react';
import './SalesChart.css';

interface SalesChartProps {
  data: SalesOverTimePoint[];
  currencySymbol?: string;
}

export const SalesChart: React.FC<SalesChartProps> = ({ data, currencySymbol = '£' }) => {
  const [range, setRange] = useState<'7' | '14' | '30'>('30');
  const [hoveredPoint, setHoveredPoint] = useState<SalesOverTimePoint | null>(null);

  const filteredData = useMemo(() => {
    const days = parseInt(range, 10);
    return data.slice(-days);
  }, [data, range]);

  const maxRevenue = useMemo(() => {
    const max = Math.max(...filteredData.map(d => d.revenue), 0);
    return max > 0 ? max : 100;
  }, [filteredData]);

  const totalPeriodRevenue = useMemo(() => {
    return filteredData.reduce((acc, curr) => acc + curr.revenue, 0);
  }, [filteredData]);

  const totalPeriodOrders = useMemo(() => {
    return filteredData.reduce((acc, curr) => acc + curr.orders_count, 0);
  }, [filteredData]);

  const chartHeight = 220;
  const chartWidth = 720;
  const paddingBottom = 30;
  const paddingTop = 20;
  const usableHeight = chartHeight - paddingBottom - paddingTop;

  return (
    <div className="sales-chart-card">
      <div className="sales-chart-header">
        <div>
          <div className="chart-title-wrap">
            <TrendingUp size={20} className="chart-icon text-primary" />
            <h3 className="chart-title">Revenue & Orders Trend</h3>
          </div>
          <p className="chart-subtitle">Verified paid customer transactions over time</p>
        </div>

        <div className="chart-controls">
          <div className="period-pills" role="radiogroup" aria-label="Select timeframe">
            <button
              type="button"
              className={`period-pill ${range === '7' ? 'active' : ''}`}
              onClick={() => setRange('7')}
            >
              7 Days
            </button>
            <button
              type="button"
              className={`period-pill ${range === '14' ? 'active' : ''}`}
              onClick={() => setRange('14')}
            >
              14 Days
            </button>
            <button
              type="button"
              className={`period-pill ${range === '30' ? 'active' : ''}`}
              onClick={() => setRange('30')}
            >
              30 Days
            </button>
          </div>
        </div>
      </div>

      <div className="chart-summary-ribbon">
        <div className="summary-metric">
          <span className="summary-label">Selected Period Revenue</span>
          <span className="summary-value">
            {currencySymbol}
            {totalPeriodRevenue.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="summary-metric">
          <span className="summary-label">Paid Orders Volume</span>
          <span className="summary-value">
            {totalPeriodOrders} {totalPeriodOrders === 1 ? 'order' : 'orders'}
          </span>
        </div>
        {hoveredPoint && (
          <div className="active-hover-badge">
            <Calendar size={13} />
            <span>{hoveredPoint.label}: </span>
            <strong>{currencySymbol}{hoveredPoint.revenue.toFixed(2)}</strong>
            <span className="orders-count-text">({hoveredPoint.orders_count} orders)</span>
          </div>
        )}
      </div>

      <div className="chart-svg-container">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="sales-svg"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#15803d" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#16a34a" stopOpacity="0.4" />
            </linearGradient>
            <linearGradient id="barHoverGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#d97706" stopOpacity="1" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.6" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
            const y = paddingTop + usableHeight * (1 - pct);
            const labelVal = (maxRevenue * pct).toFixed(0);
            return (
              <g key={idx} className="chart-grid-line">
                <line
                  x1={40}
                  y1={y}
                  x2={chartWidth - 10}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeDasharray={pct === 0 ? 'none' : '3 3'}
                  strokeWidth={1}
                />
                <text
                  x={32}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="10"
                  fill="#94a3b8"
                >
                  {currencySymbol}{labelVal}
                </text>
              </g>
            );
          })}

          {/* Bar items */}
          {filteredData.map((d, index) => {
            const count = filteredData.length;
            const barAreaWidth = (chartWidth - 50) / count;
            const barWidth = Math.max(Math.min(barAreaWidth * 0.65, 24), 6);
            const x = 45 + index * barAreaWidth + (barAreaWidth - barWidth) / 2;
            const barHeight = d.revenue > 0 ? (d.revenue / maxRevenue) * usableHeight : 3;
            const y = paddingTop + usableHeight - barHeight;
            const isHovered = hoveredPoint?.date === d.date;

            // Show date labels on spaced intervals
            const showLabel =
              count <= 10 ||
              index === 0 ||
              index === count - 1 ||
              index % Math.ceil(count / 6) === 0;

            return (
              <g
                key={d.date}
                className="chart-bar-group"
                onMouseEnter={() => setHoveredPoint(d)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  rx={3}
                  fill={isHovered ? 'url(#barHoverGradient)' : 'url(#barGradient)'}
                  className="chart-bar"
                />

                {/* Orders dot indicator if orders > 0 */}
                {d.orders_count > 0 && (
                  <circle
                    cx={x + barWidth / 2}
                    cy={y - 6}
                    r={2.5}
                    fill={isHovered ? '#b45309' : '#047857'}
                  />
                )}

                {/* Date label at bottom */}
                {showLabel && (
                  <text
                    x={x + barWidth / 2}
                    y={chartHeight - 8}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#64748b"
                    className="chart-x-label"
                  >
                    {d.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="chart-legend">
        <div className="legend-item">
          <span className="legend-swatch bar-swatch" />
          <span>Paid Revenue ({currencySymbol})</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" />
          <span>Orders Recorded</span>
        </div>
      </div>
    </div>
  );
};
