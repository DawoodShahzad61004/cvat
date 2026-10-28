// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React from 'react';
import {
    Chart, BarElement, CategoryScale, LinearScale, Legend, Tooltip, ChartData, ChartOptions,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

import { LabelCount } from './annotation-stats-page';

Chart.register(BarElement, CategoryScale, LinearScale, Legend, Tooltip);

// labels created without an explicit color have an empty one
const FALLBACK_COLOR = '#1890ff';
// one horizontal bar per label, so the chart grows with the label count instead of squeezing bars
const BAR_SLOT_HEIGHT = 24;
const AXIS_HEIGHT = 48;

// when split by type, segments are colored by type, so label colors would only add noise
const TYPE_COLORS: Record<string, string> = {
    rectangle: '#4e79a7',
    polygon: '#f28e2b',
    polyline: '#e15759',
    points: '#76b7b2',
    ellipse: '#59a14f',
    cuboid: '#edc948',
    mask: '#b07aa1',
    skeleton: '#ff9da7',
    track: '#9c755f',
    tag: '#bab0ac',
};

function makeOptions(groupedByType: boolean): ChartOptions<'bar'> {
    return {
        indexAxis: 'y',
        maintainAspectRatio: false,
        plugins: { legend: { display: groupedByType, position: 'top' } },
        scales: {
            x: {
                stacked: groupedByType, position: 'top', beginAtZero: true, ticks: { precision: 0 },
            },
            y: { stacked: groupedByType, ticks: { autoSkip: false } },
        },
    };
}

function makeData(labels: LabelCount[], groupedByType: boolean): ChartData<'bar'> {
    const names = labels.map((label) => label.name);

    if (!groupedByType) {
        return {
            labels: names,
            datasets: [{
                label: 'Annotations',
                data: labels.map((label) => label.count),
                backgroundColor: labels.map((label) => label.color || FALLBACK_COLOR),
            }],
        };
    }

    const types = [...new Set(labels.flatMap((label) => Object.keys(label.by_type ?? {})))].sort();
    return {
        labels: names,
        datasets: types.map((type) => ({
            label: type,
            data: labels.map((label) => label.by_type?.[type] ?? 0),
            backgroundColor: TYPE_COLORS[type] ?? FALLBACK_COLOR,
        })),
    };
}

interface Props {
    labels: LabelCount[];
    groupedByType: boolean;
}

function AnnotationStatsChart({ labels, groupedByType }: Props): JSX.Element {
    return (
        <div className='cvat-annotation-stats-chart' style={{ height: labels.length * BAR_SLOT_HEIGHT + AXIS_HEIGHT }}>
            <Bar data={makeData(labels, groupedByType)} options={makeOptions(groupedByType)} />
        </div>
    );
}

export default React.memo(AnnotationStatsChart);
