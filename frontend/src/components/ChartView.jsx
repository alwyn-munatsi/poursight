import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const PALETTE = ['#A8622A', '#3F6B5C', '#C9A227', '#8B4A6B', '#4B7A9B', '#B0503B'];

const TOOLTIP_STYLE = {
  backgroundColor: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  boxShadow: '0 4px 12px rgb(17 24 39 / 0.08)',
  fontSize: '0.82rem',
  color: '#111827',
};

const AXIS_TICK = { fontSize: 12, fill: '#6b7280' };

function formatLabel(key) {
  return key.replace(/_/g, ' ');
}

function SingleValue({ data }) {
  return (
    <div className="stat-grid">
      {Object.entries(data).map(([key, value]) => (
        <div className="stat-tile" key={key}>
          <div className="stat-label">{formatLabel(key)}</div>
          <div className="stat-value">{String(value)}</div>
        </div>
      ))}
    </div>
  );
}

function TableView({ data }) {
  if (!data.length) return null;
  const columns = Object.keys(data[0]);
  return (
    <div className="table-wrap">
      <table className="result-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{formatLabel(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c}>{String(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ChartView({ chart }) {
  if (!chart) return null;

  if (chart.type === 'single_value') {
    return <SingleValue data={chart.data} />;
  }
  if (chart.type === 'table') {
    return <TableView data={chart.data} />;
  }

  const data = chart.data ?? [];
  if (!data.length) return null;

  if (chart.type === 'pie') {
    return (
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="label" outerRadius={90} label>
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (chart.type === 'line') {
    return (
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
            <XAxis dataKey="label" tick={AXIS_TICK} axisLine={{ stroke: '#e5e7eb' }} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Line type="monotone" dataKey="value" stroke={PALETTE[0]} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis
            dataKey="label"
            tick={AXIS_TICK}
            axisLine={{ stroke: '#e5e7eb' }}
            tickLine={false}
            interval={0}
            angle={-20}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey="value" fill={PALETTE[0]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
