// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { Row, Col } from 'antd/lib/grid';
import Button from 'antd/lib/button';
import Empty from 'antd/lib/empty';
import Result from 'antd/lib/result';
import Switch from 'antd/lib/switch';
import Tag from 'antd/lib/tag';
import Text from 'antd/lib/typography/Text';
import Title from 'antd/lib/typography/Title';

import { getCore } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';
import AnnotationStatsChart from './annotation-stats-chart';
import { LiveStatus, useLiveAnnotationStats } from './use-live-annotation-stats';

const core = getCore();

export interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
    by_type?: Record<string, number>;
}

export interface AnnotationStats {
    task_id: number;
    total: number;
    labels: LabelCount[];
}

type StatsState =
    { status: 'loading' } |
    { status: 'failed'; message: string } |
    { status: 'loaded'; stats: AnnotationStats; groupedByType: boolean };

const LIVE_STATUS_TAGS: Record<LiveStatus, { color: string; text: string }> = {
    connecting: { color: 'default', text: 'Connecting to live updates' },
    live: { color: 'green', text: 'Live' },
    reconnecting: { color: 'orange', text: 'Connection lost, reconnecting' },
    stopped: { color: 'red', text: 'Live updates stopped' },
};

function LiveStatusTag({ status }: { status: LiveStatus }): JSX.Element {
    const { color, text } = LIVE_STATUS_TAGS[status];
    return <Tag className='cvat-annotation-stats-live-status' color={color}>{text}</Tag>;
}

function AnnotationStatsContent(
    { stats, groupedByType }: { stats: AnnotationStats; groupedByType: boolean },
): JSX.Element {
    if (!stats.labels.length) {
        return <Empty className='cvat-annotation-stats-empty' description='This task has no labels' />;
    }

    if (!stats.total) {
        return <Empty className='cvat-annotation-stats-empty' description='This task has no annotations yet' />;
    }

    return (
        <>
            <Text type='secondary'>
                {`${stats.total} annotations across ${stats.labels.length} labels`}
            </Text>
            <AnnotationStatsChart labels={stats.labels} groupedByType={groupedByType} />
        </>
    );
}

function AnnotationStatsPage(): JSX.Element {
    const taskId = +useParams<{ tid: string }>().tid;
    const [state, setState] = useState<StatsState>({ status: 'loading' });
    const [groupByType, setGroupByType] = useState(false);

    const fetchStats = useCallback(() => {
        setState({ status: 'loading' });
        core.server.request(`${core.config.backendAPI}/tasks/${taskId}/annotation-stats`, {
            method: 'GET',
            params: groupByType ? { group_by: 'type' } : {},
        })
            .then((response: { data: unknown }) => {
                // while cvat_server restarts, Traefik routes /api to the UI container, which answers with
                // index.html and status 200
                if (!Array.isArray((response.data as AnnotationStats | null)?.labels)) {
                    throw new Error('The server returned an unexpected response, it may be restarting');
                }
                setState({ status: 'loaded', stats: response.data as AnnotationStats, groupedByType: groupByType });
            })
            .catch((error: unknown) => {
                setState({ status: 'failed', message: error instanceof Error ? error.message : String(error) });
            });
    }, [taskId, groupByType]);

    useEffect(fetchStats, [fetchStats]);

    const liveStatus = useLiveAnnotationStats(
        taskId,
        groupByType,
        state.status === 'loaded',
        useCallback((stats: AnnotationStats) => {
            setState({ status: 'loaded', stats, groupedByType: groupByType });
        }, [groupByType]),
    );

    return (
        <div className='cvat-annotation-stats-page'>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14} className='cvat-task-top-bar'>
                    <GoBackButton />
                </Col>
            </Row>
            <Row justify='center' className='cvat-annotation-stats-inner-wrapper'>
                <Col span={22} xl={18} xxl={14} className='cvat-annotation-stats-inner'>
                    <div className='cvat-annotation-stats-header'>
                        <Title level={4}>{`Annotations per label — task #${taskId}`}</Title>
                        <span>
                            <Switch
                                className='cvat-annotation-stats-group-by-type'
                                checked={groupByType}
                                onChange={setGroupByType}
                            />
                            <Text className='cvat-annotation-stats-switch-label'>Split by annotation type</Text>
                        </span>
                    </div>
                    {state.status === 'loading' && <CVATLoadingSpinner />}
                    {state.status === 'failed' && (
                        <Result
                            className='cvat-annotation-stats-error'
                            status='error'
                            title='Could not load annotation statistics'
                            subTitle={state.message}
                            extra={<Button type='primary' onClick={fetchStats}>Retry</Button>}
                        />
                    )}
                    {state.status === 'loaded' && (
                        <>
                            <LiveStatusTag status={liveStatus} />
                            <AnnotationStatsContent stats={state.stats} groupedByType={state.groupedByType} />
                        </>
                    )}
                </Col>
            </Row>
        </div>
    );
}

export default React.memo(AnnotationStatsPage);
