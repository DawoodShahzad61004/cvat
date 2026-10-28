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
import Text from 'antd/lib/typography/Text';
import Title from 'antd/lib/typography/Title';

import { getCore } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';
import AnnotationStatsChart from './annotation-stats-chart';

const core = getCore();

export interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
}

export interface AnnotationStats {
    task_id: number;
    total: number;
    labels: LabelCount[];
}

type StatsState =
    { status: 'loading' } |
    { status: 'failed'; message: string } |
    { status: 'loaded'; stats: AnnotationStats };

function AnnotationStatsContent({ stats }: { stats: AnnotationStats }): JSX.Element {
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
            <AnnotationStatsChart labels={stats.labels} />
        </>
    );
}

function AnnotationStatsPage(): JSX.Element {
    const taskId = +useParams<{ tid: string }>().tid;
    const [state, setState] = useState<StatsState>({ status: 'loading' });

    const fetchStats = useCallback(() => {
        setState({ status: 'loading' });
        core.server.request(`${core.config.backendAPI}/tasks/${taskId}/annotation-stats`, { method: 'GET' })
            .then((response: { data: AnnotationStats }) => {
                setState({ status: 'loaded', stats: response.data });
            })
            .catch((error: unknown) => {
                setState({ status: 'failed', message: error instanceof Error ? error.message : String(error) });
            });
    }, [taskId]);

    useEffect(fetchStats, [fetchStats]);

    return (
        <div className='cvat-annotation-stats-page'>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14} className='cvat-task-top-bar'>
                    <GoBackButton />
                </Col>
            </Row>
            <Row justify='center' className='cvat-annotation-stats-inner-wrapper'>
                <Col span={22} xl={18} xxl={14} className='cvat-annotation-stats-inner'>
                    <Title level={4} className='cvat-annotation-stats-header'>
                        {`Annotations per label — task #${taskId}`}
                    </Title>
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
                    {state.status === 'loaded' && <AnnotationStatsContent stats={state.stats} />}
                </Col>
            </Row>
        </div>
    );
}

export default React.memo(AnnotationStatsPage);
