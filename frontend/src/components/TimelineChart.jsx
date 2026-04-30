// === FILE: src/components/TimelineChart.jsx ===
// GymSense AI — Activity timeline using Plotly.js (Light Theme)

import React, { useEffect, useRef } from 'react';

const EXERCISE_COLORS = {
  Squat: '#ef4444',
  BenchPress: '#3b82f6',
  LegPress: '#10b981',
  Adductor: '#8b5cf6',
  LegCurl: '#f59e0b',
  ArmCurl: '#14b8a6',
  RopeSkipping: '#f97316',
  Running: '#0ea5e9',
  Walking: '#22c55e',
  StairClimber: '#a855f7',
  Riding: '#ea580c',
  Null: '#e2e8f0', // Light slate color for rest/null
};

function parseTimeToSeconds(timeStr) {
  const parts = timeStr.split(':');
  return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}

export default function TimelineChart({ timeline }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!timeline || timeline.length === 0 || !chartRef.current) return;

    import('plotly.js-dist-min').then((Plotly) => {
      // Build traces grouped by exercise
      const exerciseMap = {};
      timeline.forEach((entry) => {
        const name = entry.exercise;
        if (!exerciseMap[name]) {
          exerciseMap[name] = { x: [], base: [], text: [], color: EXERCISE_COLORS[name] || '#94a3b8' };
        }
        const startSec = parseTimeToSeconds(entry.start);
        const durSec = entry.duration_s;
        exerciseMap[name].x.push(durSec / 60);
        exerciseMap[name].base.push(startSec / 60);
        exerciseMap[name].text.push(`${name}: ${entry.start}–${entry.end} (${Math.round(durSec)}s)`);
      });

      const traces = Object.entries(exerciseMap).map(([name, data]) => ({
        type: 'bar',
        orientation: 'h',
        y: data.x.map(() => 'Session'),
        x: data.x,
        base: data.base,
        name: name,
        text: data.text,
        hoverinfo: 'text',
        marker: {
          color: data.color,
          line: { color: 'rgba(255,255,255,0.5)', width: 1 },
        },
      }));

      const layout = {
        barmode: 'stack',
        showlegend: true,
        legend: {
          orientation: 'h',
          y: -0.3,
          font: { color: '#64748b', size: 11 },
          bgcolor: 'transparent',
        },
        xaxis: {
          title: { text: 'Time (minutes)', font: { color: '#64748b', size: 12 } },
          tickfont: { color: '#94a3b8' },
          gridcolor: 'rgba(0,0,0,0.05)',
          zeroline: false,
        },
        yaxis: {
          visible: false,
        },
        height: 140,
        margin: { t: 10, b: 60, l: 10, r: 10 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { family: 'Inter, system-ui, sans-serif' },
      };

      Plotly.default.newPlot(chartRef.current, traces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    });

    return () => {
      if (chartRef.current) {
        import('plotly.js-dist-min').then((Plotly) => {
          Plotly.default.purge(chartRef.current);
        });
      }
    };
  }, [timeline]);

  if (!timeline || timeline.length === 0) {
    return <p className="text-slate-400 text-sm italic">No timeline data available.</p>;
  }

  return <div ref={chartRef} id="timeline-chart" />;
}
