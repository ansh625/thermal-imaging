import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import Navbar from '../components/Navbar';
import { detectionAPI, dashboardAPI, analyticsAPI, cameraAPI } from '../services/api';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import {
  Eye, TrendingUp, BarChart3, Image as ImageIcon, RefreshCw,
  Zap, Camera, Clock, Activity, MapPin, Brain, AlertTriangle,
  Filter, Calendar, ChevronDown, ChevronUp, TrendingDown,
  Minus, Info, CheckCircle, AlertCircle
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';

// ─── Constants ────────────────────────────────────────────────────────────────

const YOLO_CLASSES = ['person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'bird', 'cat', 'dog'];

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const CLASS_COLORS = {
  person: '#3b82f6', bicycle: '#10b981', car: '#f59e0b',
  motorcycle: '#8b5cf6', bus: '#ef4444', truck: '#06b6d4',
  bird: '#f97316', cat: '#ec4899', dog: '#84cc16'
};

const getClassColor = (cls) => CLASS_COLORS[cls] || '#6366f1';

// ─── Sub-components ───────────────────────────────────────────────────────────

function TrendBadge({ pct }) {
  if (pct > 0)  return <span className="text-xs text-red-400 flex items-center gap-1"><TrendingUp size={12} />+{pct}%</span>;
  if (pct < 0)  return <span className="text-xs text-green-400 flex items-center gap-1"><TrendingDown size={12} />{pct}%</span>;
  return              <span className="text-xs text-gray-400 flex items-center gap-1"><Minus size={12} />0%</span>;
}

function InsightIcon({ type }) {
  const map = {
    warning: <AlertTriangle size={16} className="text-yellow-400 shrink-0 mt-0.5" />,
    success: <CheckCircle   size={16} className="text-green-400 shrink-0 mt-0.5" />,
    info:    <Info          size={16} className="text-blue-400  shrink-0 mt-0.5" />,
  };
  return map[type] || map.info;
}

// Custom tooltip for recharts (matches dark theme)
function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-dark-400 border border-white/10 rounded-lg p-3 text-sm shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || '#3b82f6' }}>
          {p.name || 'Count'}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
}

// ─── Filter Panel ─────────────────────────────────────────────────────────────

function FilterPanel({ filters, setFilters, cameras, onApply, loading }) {
  const [open, setOpen] = useState(false);

  const toggleClass = (cls) => {
    setFilters(f => ({  
      ...f,
      class_names: f.class_names.includes(cls)
        ? f.class_names.filter(c => c !== cls)
        : [...f.class_names, cls]
    }));
  };

  const toggleCamera = (id) => {
    setFilters(f => ({
      ...f,
      camera_ids: f.camera_ids.includes(id)
        ? f.camera_ids.filter(c => c !== id)
        : [...f.camera_ids, id]
    }));
  };

  const clearFilters = () => {
    setFilters({ date_from: '', date_to: '', class_names: [], camera_ids: [] });
  };

  const hasActiveFilters = filters.date_from || filters.date_to ||
    filters.class_names.length > 0 || filters.camera_ids.length > 0;

  return (
    <div className="glass-dark rounded-xl border border-white/10 mb-6 overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center gap-2">
          <Filter size={18} className="text-primary-400" />
          <span className="font-medium text-white">Filters</span>
          {hasActiveFilters && (
            <span className="text-xs px-2 py-0.5 bg-primary-500/20 text-primary-400 rounded-full">
              Active
            </span>
          )}
        </div>
        {open ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>

      {open && (
        <div className="p-4 pt-0 border-t border-white/5 space-y-4">
          {/* Date Range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                <Calendar size={11} /> From
              </label>
              <input
                type="date"
                value={filters.date_from}
                onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))}
                className="w-full bg-dark-400 bor   der border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                <Calendar size={11} /> To
              </label>
              <input
                type="date"
                value={filters.date_to}
                onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))}
                className="w-full bg-dark-400 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-primary-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Class Filter */}
          <div>
            <label className="text-xs text-gray-400 mb-2 block">Object Classes</label>
            <div className="flex flex-wrap gap-2">
              {YOLO_CLASSES.map(cls => (
                <button
                  key={cls}
                  onClick={() => toggleClass(cls)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all border ${
                    filters.class_names.includes(cls)
                      ? 'border-primary-500 bg-primary-500/20 text-primary-300'
                      : 'border-white/10 text-gray-400 hover:border-white/30'
                  }`}
                >
                  {cls}
                </button>
              ))}
            </div>
          </div>

          {/* Camera Filter */}
          {cameras.length > 0 && (
            <div>
              <label className="text-xs text-gray-400 mb-2 block">Cameras</label>
              <div className="flex flex-wrap gap-2">
                {cameras.map(cam => (
                  <button
                    key={cam.id}
                    onClick={() => toggleCamera(cam.id)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-all border flex items-center gap-1 ${
                      filters.camera_ids.includes(cam.id)
                        ? 'border-teal-500 bg-teal-500/20 text-teal-300'
                        : 'border-white/10 text-gray-400 hover:border-white/30'
                    }`}
                  >
                    <Camera size={10} /> {cam.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              onClick={onApply}
              disabled={loading}
              className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading…' : 'Apply Filters'}
            </button>
            {hasActiveFilters && (
              <button
                onClick={() => { clearFilters(); onApply(); }}
                className="px-4 py-2 border border-white/10 hover:border-white/30 text-gray-400 rounded-lg text-sm transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Overview Tab ─────────────────────────────────────────────────────────────

function OverviewTab({ data }) {
  const { trend_analytics, detection_counts, timeline_chart, average_detection_rate_per_hour } = data;

  return (
    <div className="space-y-6">
      {/* Trend Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-dark rounded-xl p-4 border border-white/10">
          <p className="text-xs text-gray-400 mb-1">Today</p>
          <p className="text-2xl font-bold text-white">{trend_analytics.today_count}</p>
          <TrendBadge pct={trend_analytics.day_change_pct} />
        </div>
        <div className="glass-dark rounded-xl p-4 border border-white/10">
          <p className="text-xs text-gray-400 mb-1">Yesterday</p>
          <p className="text-2xl font-bold text-white">{trend_analytics.yesterday_count}</p>
          <p className="text-xs text-gray-500">detections</p>
        </div>
        <div className="glass-dark rounded-xl p-4 border border-white/10">
          <p className="text-xs text-gray-400 mb-1">This Week</p>
          <p className="text-2xl font-bold text-white">{trend_analytics.this_week}</p>
          <TrendBadge pct={trend_analytics.week_change_pct} />
        </div>
        <div className="glass-dark rounded-xl p-4 border border-white/10">
          <p className="text-xs text-gray-400 mb-1">Avg Rate</p>
          <p className="text-2xl font-bold text-white">{average_detection_rate_per_hour}</p>
          <p className="text-xs text-gray-500">per hour</p>
        </div>
      </div>

      {/* Daily Trend Line Chart */}
      {trend_analytics.daily_series.length > 1 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-primary-400" /> Daily Detections (Last 30 Days)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend_analytics.daily_series}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickFormatter={v => v.slice(5)} // show MM-DD
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip content={<DarkTooltip />} />
              <Line
                type="monotone" dataKey="count" name="Detections"
                stroke="#3b82f6" strokeWidth={2} dot={false}
                activeDot={{ r: 4, fill: '#3b82f6' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Hourly Timeline */}
      {timeline_chart.length > 0 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Clock size={18} className="text-purple-400" /> Hourly Timeline
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={timeline_chart} barSize={6}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                tickFormatter={v => v.slice(11, 16)}
                interval={Math.floor(timeline_chart.length / 8)}
              />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" name="Detections" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Object Frequency Bar Chart */}
      {detection_counts.by_class.length > 0 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-green-400" /> Object Frequency
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={detection_counts.by_class} layout="vertical" barSize={20}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis
                type="category" dataKey="class_name"
                tick={{ fill: '#d1d5db', fontSize: 12 }}
                width={80}
              />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                {detection_counts.by_class.map((entry) => (
                  <Cell key={entry.class_name} fill={getClassColor(entry.class_name)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ─── Activity Tab ─────────────────────────────────────────────────────────────

function ActivityTab({ data }) {
  const { activity_intensity, peak_hours } = data;

  // Build 24×7 matrix
  const maxCount = Math.max(...activity_intensity.map(d => d.count), 1);
  const grid = {};
  activity_intensity.forEach(d => { grid[`${d.hour}-${d.weekday}`] = d.count; });

  const cellOpacity = (count) => count === 0 ? 0.04 : 0.1 + (count / maxCount) * 0.9;

  return (
    <div className="space-y-6">
      {/* Heatmap */}
      <div className="glass-dark rounded-xl p-6 border border-white/10">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Activity size={18} className="text-orange-400" /> Activity Heatmap (Hour × Day)
        </h3>
        <div className="overflow-x-auto">
          <div className="min-w-max">
            {/* Day labels */}
            <div className="flex mb-1 ml-12">
              {WEEKDAY_LABELS.map(d => (
                <div key={d} className="w-9 text-center text-xs text-gray-500">{d}</div>
              ))}
            </div>
            {/* Rows: one per hour */}
            {Array.from({ length: 24 }, (_, h) => (
              <div key={h} className="flex items-center mb-0.5">
                <div className="w-10 text-right pr-2 text-xs text-gray-500">{`${h.toString().padStart(2,'0')}:00`}</div>
                {Array.from({ length: 7 }, (_, w) => {
                  const count = grid[`${h}-${w}`] || 0;
                  return (
                    <div
                      key={w}
                      className="w-9 h-7 mx-0.5 rounded-sm flex items-center justify-center text-xs cursor-default transition-all"
                      style={{ backgroundColor: `rgba(59,130,246,${cellOpacity(count)})` }}
                      title={`${WEEKDAY_LABELS[w]} ${h.toString().padStart(2,'0')}:00 — ${count} detections`}
                    >
                      {count > 0 && <span className="text-white/70" style={{ fontSize: 9 }}>{count}</span>}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <span className="text-xs text-gray-500">Low</span>
          {[0.04, 0.2, 0.4, 0.65, 0.9].map((op, i) => (
            <div key={i} className="w-6 h-4 rounded-sm" style={{ backgroundColor: `rgba(59,130,246,${op})` }} />
          ))}
          <span className="text-xs text-gray-500">High</span>
        </div>
      </div>

      {/* Peak Hours Bar Chart */}
      {peak_hours.length > 0 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Zap size={18} className="text-yellow-400" /> Peak Detection Hours
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={peak_hours} barSize={32}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="label" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" name="Detections" fill="#f59e0b" radius={[4, 4, 0, 0]}>
                {peak_hours.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={i === 0 ? '#f59e0b' : i === 1 ? '#fb923c' : '#6366f1'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ─── Zones Tab ────────────────────────────────────────────────────────────────

function ZonesTab({ data }) {
  const { zone_analytics } = data;
  const maxZone = Math.max(...zone_analytics.map(z => z.count), 1);
  const zoneMap = {};
  zone_analytics.forEach(z => { zoneMap[z.zone] = z.count; });

  const ZONE_ORDER = [
    ['Top-Left', 'Top-Center', 'Top-Right'],
    ['Mid-Left', 'Mid-Center', 'Mid-Right'],
    ['Bot-Left', 'Bot-Center', 'Bot-Right']
  ];

  return (
    <div className="space-y-6">
      <div className="glass-dark rounded-xl p-6 border border-white/10">
        <h3 className="text-white font-semibold mb-2 flex items-center gap-2">
          <MapPin size={18} className="text-teal-400" /> Zone Activity Map
        </h3>
        <p className="text-xs text-gray-500 mb-6">
          Zones are based on the bounding box centre position within the 1280×720 frame.
        </p>

        {/* Frame outline */}
        <div className="relative mx-auto" style={{ maxWidth: 480 }}>
          <div className="aspect-video border-2 border-white/20 rounded-lg overflow-hidden grid grid-cols-3 grid-rows-3 gap-0.5 bg-white/5 p-0.5">
            {ZONE_ORDER.flat().map(zoneName => {
              const count = zoneMap[zoneName] || 0;
              const intensity = count / maxZone;
              return (
                <div
                  key={zoneName}
                  className="relative flex flex-col items-center justify-center rounded p-2 transition-all"
                  style={{ backgroundColor: `rgba(59,130,246,${0.05 + intensity * 0.55})` }}
                >
                  <span className="text-xs text-gray-400 text-center leading-tight">{zoneName}</span>
                  <span className="text-lg font-bold text-white mt-1">{count}</span>
                  {count === Math.max(...Object.values(zoneMap)) && count > 0 && (
                    <span className="absolute top-1 right-1 w-2 h-2 bg-yellow-400 rounded-full" title="Most active zone" />
                  )}
                </div>
              );
            })}
          </div>
          <p className="text-center text-xs text-gray-500 mt-2">Camera field of view</p>
        </div>

        {/* Zone table */}
        <div className="mt-6 space-y-2">
          {zone_analytics
            .filter(z => z.count > 0)
            .sort((a, b) => b.count - a.count)
            .map(z => (
              <div key={z.zone} className="flex items-center gap-3">
                <span className="w-24 text-sm text-gray-300">{z.zone}</span>
                <div className="flex-1 h-2 bg-dark-400 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-teal-500 rounded-full"
                    style={{ width: `${(z.count / maxZone) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-400 w-12 text-right">{z.count}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

// ─── Insights Tab ─────────────────────────────────────────────────────────────

function InsightsTab({ data }) {
  const {
    smart_insights, alert_analytics, camera_analytics,
    no_activity_periods, object_analytics
  } = data;

  return (
    <div className="space-y-6">
      {/* Smart Insights */}
      <div className="glass-dark rounded-xl p-6 border border-white/10">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Brain size={18} className="text-purple-400" /> Smart Insights
        </h3>
        <div className="space-y-3">
          {smart_insights.map((ins, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`flex gap-3 p-3 rounded-lg border ${
                ins.type === 'warning'
                  ? 'bg-yellow-500/5 border-yellow-500/20'
                  : ins.type === 'success'
                  ? 'bg-green-500/5 border-green-500/20'
                  : 'bg-blue-500/5 border-blue-500/20'
              }`}
            >
              <InsightIcon type={ins.type} />
              <p className="text-sm text-gray-300">{ins.text}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Alert Analytics */}
      <div className="glass-dark rounded-xl p-6 border border-white/10">
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle size={18} className="text-yellow-400" /> Alert Analytics
          <span className="ml-auto text-xs text-gray-500">
            High-confidence detections ≥{Math.round(alert_analytics.threshold * 100)}%
          </span>
        </h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/20">
            <p className="text-3xl font-bold text-yellow-400">{alert_analytics.total_alerts}</p>
            <p className="text-xs text-gray-400 mt-1">Total Alerts</p>
          </div>
          <div className="bg-dark-400 rounded-lg p-4 border border-white/10">
            <p className="text-3xl font-bold text-white">{alert_analytics.alert_rate_pct}%</p>
            <p className="text-xs text-gray-400 mt-1">Alert Rate</p>
          </div>
        </div>
        {alert_analytics.by_class.length > 0 && (
          <div className="space-y-2">
            {alert_analytics.by_class.map(a => (
              <div key={a.class_name} className="flex items-center justify-between py-1">
                <span className="text-sm capitalize text-gray-300">{a.class_name}</span>
                <span className="text-sm font-medium text-yellow-400">{a.count} alerts</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Object-wise Table */}
      {object_analytics.length > 0 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-blue-400" /> Object-wise Analytics
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  {['Class', 'Count', 'Share', 'Avg Conf', 'Today', 'Yesterday', 'Trend'].map(h => (
                    <th key={h} className="pb-2 text-left text-xs text-gray-500 font-medium pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {object_analytics.map(obj => (
                  <tr key={obj.class_name} className="border-b border-white/5 hover:bg-white/3">
                    <td className="py-2 pr-4">
                      <span className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getClassColor(obj.class_name) }}
                        />
                        <span className="capitalize text-white">{obj.class_name}</span>
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-white font-medium">{obj.count}</td>
                    <td className="py-2 pr-4 text-gray-400">{obj.percentage}%</td>
                    <td className="py-2 pr-4 text-gray-400">{obj.avg_confidence}%</td>
                    <td className="py-2 pr-4 text-gray-300">{obj.today_count}</td>
                    <td className="py-2 pr-4 text-gray-300">{obj.yesterday_count}</td>
                    <td className="py-2"><TrendBadge pct={obj.trend_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Camera-wise Analytics */}
      {camera_analytics.length > 0 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Camera size={18} className="text-teal-400" /> Camera-wise Analytics
          </h3>
          <div className="space-y-3">
            {camera_analytics.map(cam => (
              <div key={cam.camera_id} className="flex items-center gap-4 p-3 bg-dark-400 rounded-lg">
                <div className="w-8 h-8 rounded-lg bg-teal-500/20 flex items-center justify-center shrink-0">
                  <Camera size={14} className="text-teal-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">{cam.camera_name}</p>
                  <p className="text-xs text-gray-500">
                    Last: {cam.last_detection || 'N/A'}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-white font-bold">{cam.count}</p>
                  <p className="text-xs text-gray-400">{cam.avg_confidence}% conf</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No-Activity Periods */}
      {no_activity_periods.length > 0 && (
        <div className="glass-dark rounded-xl p-6 border border-white/10">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Clock size={18} className="text-gray-400" /> Longest Quiet Periods
          </h3>
          <div className="space-y-2">
            {no_activity_periods.map((gap, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-dark-400 rounded-lg text-sm">
                <span className="text-gray-400">{gap.from} → {gap.to}</span>
                <span className="text-gray-300 font-medium ml-4 shrink-0">
                  {gap.duration_minutes} min
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Analytics Component ─────────────────────────────────────────────────

export default function Analytics() {
  const { token } = useAuthStore();
  const navigate = useNavigate();

  // ── Existing state (UNCHANGED) ──
  const [detections, setDetections]   = useState([]);
  const [stats, setStats]             = useState(null);
  const [loading, setLoading]         = useState(true);
  const [activeTab, setActiveTab]     = useState('detections');
  const [refreshing, setRefreshing]   = useState(false);

  // ── New state ──
  const [advancedData, setAdvancedData]     = useState(null);
  const [advancedLoading, setAdvancedLoading] = useState(false);
  const [cameras, setCameras]               = useState([]);
  const [filters, setFilters]               = useState({
    date_from: '', date_to: '', class_names: [], camera_ids: []
  });

  useEffect(() => {
    if (!token) navigate('/login');
    else {
      loadData();
      loadCameras();
      loadAdvanced();
    }
  }, [token, navigate]);

  // Auto-refresh every 10 seconds (UNCHANGED behaviour)
  useEffect(() => {
    const interval = setInterval(() => { loadData(); }, 10000);
    return () => clearInterval(interval);
  }, []);

  // ── Existing loadData (UNCHANGED) ──
  const loadData = async () => {
    try {
      const [detectionsRes, statsRes] = await Promise.all([
        detectionAPI.list(100),
        dashboardAPI.getStats()
      ]);
      setDetections(detectionsRes.data.detections);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      if (loading) toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ── New: load cameras for filter dropdown ──
  const loadCameras = async () => {
    try {
      const res = await cameraAPI.list();
      setCameras(res.data.cameras || []);
    } catch { /* silent */ }
  };

  // ── New: load advanced analytics ──
  const loadAdvanced = useCallback(async (customFilters) => {
    setAdvancedLoading(true);
    try {
      const res = await analyticsAPI.getAdvanced(customFilters ?? filters);
      setAdvancedData(res.data);
    } catch (error) {
      console.error('Failed to load advanced analytics:', error);
      toast.error('Failed to load advanced analytics');
    } finally {
      setAdvancedLoading(false);
    }
  }, [filters]);

  const handleManualRefresh = async () => {
    setRefreshing(true);
    await loadData();
    await loadAdvanced();
  };

  // ── Existing helper (UNCHANGED) ──
  const getDetectionsByClass = () => {
    const counts = {};
    detections.forEach(det => {
      counts[det.class_name] = (counts[det.class_name] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  };

  const ADVANCED_TABS = ['overview', 'activity', 'zones', 'insights'];
  const isAdvancedTab = ADVANCED_TABS.includes(activeTab);

  return (
    <div className="min-h-screen bg-dark-500">
      <Navbar />

      <div className="p-6">
        {/* Header (UNCHANGED structure) */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
            <p className="text-gray-400">View detection statistics and insights</p>
          </div>
          <button
            onClick={handleManualRefresh}
            disabled={refreshing || loading}
            className={`p-2 rounded-xl border border-white/10 transition-all ${
              refreshing || loading
                ? 'bg-primary-500/20 text-primary-400 animate-spin'
                : 'hover:border-primary-500/50 text-gray-400 hover:text-primary-400'
            }`}
            title="Refresh"
          >
            <RefreshCw size={24} />
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Stats Cards (UNCHANGED) */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <Eye className="text-primary-400" size={24} />
                  <span className="text-xs text-gray-400">Total</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats?.total_detections || 0}</p>
                <p className="text-sm text-gray-400">Detections</p>
              </div>
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <TrendingUp className="text-green-400" size={24} />
                  <span className="text-xs text-gray-400">Today</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {detections.filter(d =>
                    new Date(d.detected_at).toDateString() === new Date().toDateString()
                  ).length}
                </p>
                <p className="text-sm text-gray-400">New Detections</p>
              </div>
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <BarChart3 className="text-purple-400" size={24} />
                  <span className="text-xs text-gray-400">Types</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {getDetectionsByClass().length}
                </p>
                <p className="text-sm text-gray-400">Object Classes</p>
              </div>
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <ImageIcon className="text-orange-400" size={24} />
                  <span className="text-xs text-gray-400">Storage</span>
                </div>
                <p className="text-3xl font-bold text-white">
                  {stats?.storage_breakdown?.detections_gb || 0}
                </p>
                <p className="text-sm text-gray-400">GB Used</p>
              </div>
            </div>

            {/* Filter Panel — only visible when on advanced tabs */}
            {isAdvancedTab && (
              <FilterPanel
                filters={filters}
                setFilters={setFilters}
                cameras={cameras}
                onApply={() => loadAdvanced()}
                loading={advancedLoading}
              />
            )}

            {/* Tabs */}
            <div className="flex gap-4 mb-6 border-b border-white/10 overflow-x-auto">
              {[
                { id: 'detections', label: 'Detection History', icon: <Eye size={14} /> },
                { id: 'stats',      label: 'Statistics',        icon: <BarChart3 size={14} /> },
                { id: 'overview',   label: 'Overview',          icon: <TrendingUp size={14} /> },
                { id: 'activity',   label: 'Activity',          icon: <Activity size={14} /> },
                { id: 'zones',      label: 'Zones',             icon: <MapPin size={14} /> },
                { id: 'insights',   label: 'Insights',          icon: <Brain size={14} /> },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`pb-3 px-1 font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0 ${
                    activeTab === tab.id
                      ? 'text-primary-400 border-b-2 border-primary-400'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {tab.icon}{tab.label}
                </button>
              ))}
            </div>

            {/* ── Tab Content ── */}

            {/* Detection History (UNCHANGED) */}
            {activeTab === 'detections' && (
              detections.length === 0 ? (
                <div className="glass-dark rounded-xl p-12 text-center border border-white/10">
                  <Eye size={64} className="mx-auto text-gray-600 mb-4" />
                  <h3 className="text-xl font-semibold text-white mb-2">No Detections Yet</h3>
                  <p className="text-gray-400">Enable object detection to start tracking</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {detections.map((detection, index) => (
                    <motion.div
                      key={detection.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.03 }}
                      className="glass-dark rounded-xl overflow-hidden border border-white/10 hover:border-primary-500/50 transition-all"
                    >
                      {detection.screenshot_path ? (
                        <img
                          src={`http://localhost:8000/${detection.screenshot_path}`}
                          alt={detection.class_name}
                          className="w-full h-40 object-cover"
                        />
                      ) : (
                        <div className="w-full h-40 bg-dark-400 flex items-center justify-center">
                          <ImageIcon className="text-gray-600" size={32} />
                        </div>
                      )}
                      <div className="p-3">
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="font-semibold text-white capitalize">
                            {detection.class_name}
                          </h4>
                          <span className="text-xs px-2 py-1 bg-primary-500/20 text-primary-400 rounded">
                            {(detection.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-400">
                          {new Date(detection.detected_at).toLocaleString()}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )
            )}

            {/* Statistics (UNCHANGED) */}
            {activeTab === 'stats' && (
              <div className="glass-dark rounded-xl p-6 border border-white/10">
                <h3 className="text-xl font-semibold text-white mb-6">Detection Statistics</h3>
                <div className="space-y-4">
                  {getDetectionsByClass().map(([className, count]) => (
                    <div key={className} className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-white capitalize font-medium">{className}</span>
                          <span className="text-gray-400">{count} detections</span>
                        </div>
                        <div className="h-2 bg-dark-400 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 rounded-full"
                            style={{ width: `${(count / detections.length) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Advanced Tabs — show loader if data not ready */}
            {isAdvancedTab && (
              advancedLoading || !advancedData ? (
                <div className="flex justify-center items-center h-64">
                  <div className="w-10 h-10 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
                </div>
              ) : (
                <>
                  {activeTab === 'overview'  && <OverviewTab  data={advancedData} />}
                  {activeTab === 'activity'  && <ActivityTab  data={advancedData} />}
                  {activeTab === 'zones'     && <ZonesTab     data={advancedData} />}
                  {activeTab === 'insights'  && <InsightsTab  data={advancedData} />}
                </>
              )
            )}
          </>
        )}
      </div>
    </div>
  );
}
