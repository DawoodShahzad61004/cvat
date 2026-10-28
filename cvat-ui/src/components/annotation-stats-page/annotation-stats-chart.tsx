// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React from 'react';
import {
    Chart, BarElement, CategoryScale, LinearScale, Tooltip, ChartData, ChartOptions,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

import { LabelCount } from './annotation-stats-page';

Chart.register(BarElement, CategoryScale, LinearScale, Tooltip);

// labels created without an explicit color have an empty one
const FALLBACK_COLOR = '#1890ff';
// one horizontal bar per label, so the chart grows with the label count instead of squeezing bars
const BAR_SLOT_HEIGHT = 24;
const AXIS_HEIGHT = 48;

const options: ChartOptions<'bar'> = {
    indexAxis: 'y',
    maintainAspectRatio: false,
    scales: {
        x: { beginAtZero: true, ticks: { precision: 0 } },
        y: { ticks: { autoSkip: false } },
    },
};

function AnnotationStatsChart({ labels }: { labels: LabelCount[] }): JSX.Element {
    const data: ChartData<'bar'> = {
        labels: labels.map((label) => label.name),
        datasets: [{
            label: 'Annotations',
            data: labels.map((label) => label.count),
            backgroundColor: labels.map((label) => label.color || FALLBACK_COLOR),
        }],
    };

    return (
        <div className='cvat-annotation-stats-chart' style={{ height: labels.length * BAR_SLOT_HEIGHT + AXIS_HEIGHT }}>
            <Bar data={data} options={options} />
        </div>
    );
}

export default React.memo(AnnotationStatsChart);
