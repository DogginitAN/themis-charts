/**
 * THEMIS Chart Component - Next.js/React
 * TradingView Lightweight Charts with security mention markers
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';

interface MentionData {
  date: string;
  mention_count: number;
  video_titles?: string[];
  channel_names?: string[];
  themes?: string[];
}

interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChartData {
  symbol: string;
  prices: PriceData[];
  mentions: MentionData[];
}

interface ThemisChartProps {
  symbol: string;
  data: ChartData;
  height?: number;
  showVolume?: boolean;
  showMentions?: boolean;
}

export default function ThemisChart({
  symbol,
  data,
  height = 600,
  showVolume = true,
  showMentions = true,
}: ThemisChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const [hoveredMention, setHoveredMention] = useState<MentionData | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data.prices.length) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#1E1E1E' },
        textColor: '#D9D9D9',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: {
        mode: 1, // Normal crosshair
      },
      rightPriceScale: {
        borderColor: '#2B2B43',
      },
      timeScale: {
        borderColor: '#2B2B43',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Format price data
    const priceData = data.prices.map((p) => ({
      time: p.date as UTCTimestamp,
      open: p.open,
      high: p.high,
      low: p.low,
      close: p.close,
    }));

    candlestickSeries.setData(priceData);

    // Add volume series
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume',
      });

      volumeSeriesRef.current = volumeSeries;

      // Format volume data
      const volumeData = data.prices.map((p) => ({
        time: p.date as UTCTimestamp,
        value: p.volume,
        color: p.close >= p.open ? '#26a69a80' : '#ef535080', // Semi-transparent
      }));

      volumeSeries.setData(volumeData);

      // Create separate price scale for volume
      chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.8, // Volume at bottom 20%
          bottom: 0,
        },
      });
    }

    // Add mention markers
    if (showMentions && data.mentions.length > 0) {
      const mentionMap = new Map(data.mentions.map((m) => [m.date, m]));

      const markers = data.mentions
        .filter((m) => m.mention_count > 0)
        .map((m) => {
          // Find the price bar for this date
          const priceBar = data.prices.find((p) => p.date === m.date);
          if (!priceBar) return null;

          return {
            time: m.date as UTCTimestamp,
            position: 'aboveBar' as const,
            color: '#2196F3',
            shape: 'arrowDown' as const,
            text: m.mention_count > 1 ? `${m.mention_count}` : '',
            size: Math.min(m.mention_count * 0.5 + 1, 3),
          };
        })
        .filter((m) => m !== null);

      candlestickSeries.setMarkers(markers as any);
    }

    // Auto-scale to fit content
    chart.timeScale().fitContent();

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, height, showVolume, showMentions]);

  // Calculate stats
  const totalMentions = data.mentions.reduce((sum, m) => sum + m.mention_count, 0);
  const daysWithMentions = data.mentions.filter((m) => m.mention_count > 0).length;
  const priceChange =
    data.prices.length > 1
      ? ((data.prices[data.prices.length - 1].close - data.prices[0].close) /
          data.prices[0].close) *
        100
      : 0;

  return (
    <div className="themis-chart-wrapper">
      {/* Stats Header */}
      <div className="chart-stats">
        <div className="stat-item">
          <span className="stat-label">Symbol</span>
          <span className="stat-value">{symbol}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Total Mentions</span>
          <span className="stat-value">{totalMentions}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Days with Mentions</span>
          <span className="stat-value">{daysWithMentions}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Price Change</span>
          <span className={`stat-value ${priceChange >= 0 ? 'positive' : 'negative'}`}>
            {priceChange >= 0 ? '+' : ''}
            {priceChange.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Chart Container */}
      <div ref={chartContainerRef} className="chart-container" />

      {/* Mention Details Tooltip */}
      {hoveredMention && (
        <div className="mention-tooltip">
          <div className="tooltip-header">
            <strong>{hoveredMention.mention_count} Mentions</strong>
            <span>{hoveredMention.date}</span>
          </div>
          {hoveredMention.channel_names && (
            <div className="tooltip-section">
              <span className="tooltip-label">Channels:</span>
              <span>{hoveredMention.channel_names.join(', ')}</span>
            </div>
          )}
          {hoveredMention.themes && hoveredMention.themes.length > 0 && (
            <div className="tooltip-section">
              <span className="tooltip-label">Themes:</span>
              <span>{hoveredMention.themes.slice(0, 3).join(', ')}</span>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .themis-chart-wrapper {
          width: 100%;
          background: #1e1e1e;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        .chart-stats {
          display: flex;
          justify-content: space-around;
          margin-bottom: 16px;
          padding: 12px;
          background: #2a2a2a;
          border-radius: 6px;
        }

        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }

        .stat-label {
          font-size: 12px;
          color: #888;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .stat-value {
          font-size: 18px;
          font-weight: bold;
          color: #fff;
        }

        .stat-value.positive {
          color: #26a69a;
        }

        .stat-value.negative {
          color: #ef5350;
        }

        .chart-container {
          width: 100%;
          position: relative;
        }

        .mention-tooltip {
          position: absolute;
          top: 80px;
          right: 20px;
          background: #2a2a2a;
          border: 1px solid #444;
          border-radius: 6px;
          padding: 12px;
          min-width: 250px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
          z-index: 10;
        }

        .tooltip-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
          padding-bottom: 8px;
          border-bottom: 1px solid #444;
          color: #fff;
        }

        .tooltip-section {
          margin-top: 8px;
          font-size: 13px;
          color: #ccc;
        }

        .tooltip-label {
          font-weight: bold;
          color: #2196f3;
          margin-right: 8px;
        }
      `}</style>
    </div>
  );
}
